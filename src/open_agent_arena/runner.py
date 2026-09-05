"""Match orchestration with append-only event logging."""

from __future__ import annotations

import json
import time
import uuid
from collections.abc import Mapping
from dataclasses import asdict, dataclass, field, replace
from pathlib import Path
from typing import Any, TextIO

from .core import (
    Action,
    AgentBudget,
    AgentDecision,
    AgentTimeoutError,
    AgentUsage,
    ArenaAgent,
    ArenaEnvironment,
)


@dataclass(slots=True)
class _UsageCounter:
    decisions: int = 0
    latency_ms: float = 0.0
    input_tokens: int = 0
    output_tokens: int = 0
    model_calls: int = 0
    tool_calls: int = 0
    cost_usd: float = 0.0
    timeouts: int = 0
    budget_exhaustions: int = 0

    def add(self, usage: AgentUsage, latency_ms: float) -> None:
        self.decisions += 1
        self.latency_ms += latency_ms
        self.input_tokens += usage.input_tokens
        self.output_tokens += usage.output_tokens
        self.model_calls += usage.model_calls
        self.tool_calls += usage.tool_calls
        self.cost_usd += usage.cost_usd

    def public(self) -> dict[str, int | float]:
        result = asdict(self)
        result["latency_ms"] = round(self.latency_ms, 3)
        result["cost_usd"] = round(self.cost_usd, 8)
        return result


@dataclass(frozen=True, slots=True)
class MatchSummary:
    match_id: str
    environment: str
    seed: int
    winner: str | None
    turns: int
    scores: Mapping[str, float]
    invalid_actions: Mapping[str, int]
    agent_errors: Mapping[str, int]
    telemetry: Mapping[str, Mapping[str, int | float]] = field(default_factory=dict)


class MatchRunner:
    """Run one match while keeping policy code outside environment state."""

    def __init__(
        self,
        environment: ArenaEnvironment,
        agents: Mapping[str, ArenaAgent],
        *,
        fallback_action: str = "harvest",
        budgets: Mapping[str, AgentBudget] | AgentBudget | None = None,
    ) -> None:
        missing = set(environment.agents) - set(agents)
        if missing:
            raise ValueError(f"missing agents: {sorted(missing)}")
        self.environment = environment
        self.agents = agents
        self.fallback_action = fallback_action
        if budgets is None:
            self.budgets = {agent_id: AgentBudget() for agent_id in environment.agents}
        elif isinstance(budgets, AgentBudget):
            self.budgets = {agent_id: budgets for agent_id in environment.agents}
        else:
            self.budgets = {
                agent_id: budgets.get(agent_id, AgentBudget())
                for agent_id in environment.agents
            }

    def run(self, *, seed: int, log_path: str | Path | None = None) -> MatchSummary:
        match_id = str(uuid.uuid4())
        observations = self.environment.reset(seed)
        agent_errors = {agent_id: 0 for agent_id in self.environment.agents}
        invalid_actions = {agent_id: 0 for agent_id in self.environment.agents}
        usage_totals = {agent_id: _UsageCounter() for agent_id in self.environment.agents}
        turn = 0

        handle: TextIO | None = None
        if log_path is not None:
            path = Path(log_path)
            path.parent.mkdir(parents=True, exist_ok=True)
            handle = path.open("w", encoding="utf-8")

        try:
            self._write(
                handle,
                {
                    "schema_version": "arena.trace/v1",
                    "type": "match_started",
                    "match_id": match_id,
                    "environment": self.environment.environment_id,
                    "seed": seed,
                    "agents": list(self.environment.agents),
                    "budgets": {
                        agent_id: asdict(budget) for agent_id, budget in self.budgets.items()
                    },
                },
            )
            done = False
            while not done:
                turn += 1
                actions: dict[str, Action] = {}
                telemetry: dict[str, dict[str, Any]] = {}

                for agent_id in self.environment.agents:
                    budget = self.budgets[agent_id]
                    counter = usage_totals[agent_id]
                    agent_observation = replace(
                        observations[agent_id],
                        budget_remaining=self._budget_remaining(budget, counter),
                    )
                    started = time.perf_counter()
                    error: str | None = None
                    timed_out = False
                    budget_exhausted = False
                    usage = AgentUsage()
                    metadata: Mapping[str, Any] = {}
                    depleted = self._depleted_budget(budget, counter)
                    if depleted:
                        action = Action(self.fallback_action)
                        budget_exhausted = True
                        counter.budget_exhaustions += 1
                        error = f"budget exhausted: {', '.join(depleted)}"
                    else:
                        try:
                            response = self.agents[agent_id].act(agent_observation)
                            if isinstance(response, AgentDecision):
                                action = response.action
                                usage = response.usage
                                metadata = response.metadata
                            elif isinstance(response, Action):
                                action = response
                            else:
                                raise TypeError("agent must return Action or AgentDecision")
                        except AgentTimeoutError as exc:
                            counter.timeouts += 1
                            timed_out = True
                            action = Action(self.fallback_action)
                            error = f"{type(exc).__name__}: {exc}"
                        except Exception as exc:  # contain agent failures at the runner boundary
                            agent_errors[agent_id] += 1
                            action = Action(self.fallback_action)
                            error = f"{type(exc).__name__}: {exc}"
                    latency_ms = (time.perf_counter() - started) * 1000
                    counter.add(usage, latency_ms)
                    if not depleted and not timed_out and latency_ms > budget.decision_timeout_ms:
                        counter.timeouts += 1
                        timed_out = True
                        action = Action(self.fallback_action)
                        error = error or (
                            f"decision exceeded {budget.decision_timeout_ms} ms deadline"
                        )
                    exceeded = [] if depleted else self._exceeded_budget(budget, counter)
                    if exceeded:
                        counter.budget_exhaustions += 1
                        budget_exhausted = True
                        action = Action(self.fallback_action)
                        error = error or f"budget exhausted: {', '.join(exceeded)}"
                    actions[agent_id] = action
                    telemetry[agent_id] = {
                        "latency_ms": round(latency_ms, 3),
                        "error": error,
                        "timed_out": timed_out,
                        "budget_exhausted": budget_exhausted,
                        "usage": asdict(usage),
                        "cumulative": counter.public(),
                        "metadata": dict(metadata),
                    }

                result = self.environment.step(actions)
                for agent_id in result.info.get("invalid_actions", []):
                    invalid_actions[agent_id] += 1

                self._write(
                    handle,
                    {
                        "schema_version": "arena.trace/v1",
                        "type": "step",
                        "match_id": match_id,
                        "turn": turn,
                        "observations": {
                            agent_id: asdict(observation)
                            for agent_id, observation in observations.items()
                        },
                        "actions": {
                            agent_id: asdict(action) for agent_id, action in actions.items()
                        },
                        "rewards": dict(result.rewards),
                        "terminated": result.terminated,
                        "truncated": result.truncated,
                        "info": dict(result.info),
                        "telemetry": telemetry,
                    },
                )
                observations = result.observations
                done = result.terminated or result.truncated

            scores = dict(self.environment.scores())
            winner = self._winner(scores)
            summary = MatchSummary(
                match_id=match_id,
                environment=self.environment.environment_id,
                seed=seed,
                winner=winner,
                turns=turn,
                scores=scores,
                invalid_actions=invalid_actions,
                agent_errors=agent_errors,
                telemetry={
                    agent_id: counter.public() for agent_id, counter in usage_totals.items()
                },
            )
            self._write(
                handle,
                {
                    "schema_version": "arena.trace/v1",
                    "type": "match_finished",
                    "match_id": match_id,
                    **asdict(summary),
                },
            )
            return summary
        finally:
            if handle is not None:
                handle.close()

    @staticmethod
    def _winner(scores: Mapping[str, float]) -> str | None:
        ordered = sorted(scores.items(), key=lambda item: item[1], reverse=True)
        if len(ordered) < 2 or ordered[0][1] == ordered[1][1]:
            return None
        return ordered[0][0]

    @staticmethod
    def _budget_remaining(
        budget: AgentBudget, counter: _UsageCounter
    ) -> dict[str, int | float | None]:
        def remaining(limit: int | float | None, used: int | float) -> int | float | None:
            return None if limit is None else max(0, limit - used)

        return {
            "decision_timeout_ms": budget.decision_timeout_ms,
            "input_tokens": remaining(budget.max_input_tokens, counter.input_tokens),
            "output_tokens": remaining(budget.max_output_tokens, counter.output_tokens),
            "model_calls": remaining(budget.max_model_calls, counter.model_calls),
            "tool_calls": remaining(budget.max_tool_calls, counter.tool_calls),
            "cost_usd": remaining(budget.max_cost_usd, counter.cost_usd),
        }

    @staticmethod
    def _exceeded_budget(budget: AgentBudget, counter: _UsageCounter) -> list[str]:
        limits = {
            "input_tokens": (budget.max_input_tokens, counter.input_tokens),
            "output_tokens": (budget.max_output_tokens, counter.output_tokens),
            "model_calls": (budget.max_model_calls, counter.model_calls),
            "tool_calls": (budget.max_tool_calls, counter.tool_calls),
            "cost_usd": (budget.max_cost_usd, counter.cost_usd),
        }
        return [
            name
            for name, (limit, used) in limits.items()
            if limit is not None and used > limit
        ]

    @staticmethod
    def _depleted_budget(budget: AgentBudget, counter: _UsageCounter) -> list[str]:
        limits = {
            "input_tokens": (budget.max_input_tokens, counter.input_tokens),
            "output_tokens": (budget.max_output_tokens, counter.output_tokens),
            "model_calls": (budget.max_model_calls, counter.model_calls),
            "tool_calls": (budget.max_tool_calls, counter.tool_calls),
            "cost_usd": (budget.max_cost_usd, counter.cost_usd),
        }
        return [
            name
            for name, (limit, used) in limits.items()
            if limit is not None and used >= limit
        ]

    @staticmethod
    def _write(handle: TextIO | None, record: Mapping[str, Any]) -> None:
        if handle is not None:
            handle.write(json.dumps(record, ensure_ascii=False, separators=(",", ":")) + "\n")
            handle.flush()
