"""Match orchestration with append-only event logging."""

from __future__ import annotations

import json
import time
import uuid
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any, Mapping, TextIO

from .core import Action, ArenaAgent, ArenaEnvironment, Observation


@dataclass(frozen=True, slots=True)
class MatchSummary:
    environment: str
    seed: int
    winner: str | None
    turns: int
    scores: Mapping[str, float]
    invalid_actions: Mapping[str, int]
    agent_errors: Mapping[str, int]


class MatchRunner:
    """Run one match while keeping policy code outside environment state."""

    def __init__(
        self,
        environment: ArenaEnvironment,
        agents: Mapping[str, ArenaAgent],
        *,
        fallback_action: str = "harvest",
    ) -> None:
        missing = set(environment.agents) - set(agents)
        if missing:
            raise ValueError(f"missing agents: {sorted(missing)}")
        self.environment = environment
        self.agents = agents
        self.fallback_action = fallback_action

    def run(self, *, seed: int, log_path: str | Path | None = None) -> MatchSummary:
        match_id = str(uuid.uuid4())
        observations = self.environment.reset(seed)
        agent_errors = {agent_id: 0 for agent_id in self.environment.agents}
        invalid_actions = {agent_id: 0 for agent_id in self.environment.agents}
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
                    "schema_version": "arena.trace/v0",
                    "type": "match_started",
                    "match_id": match_id,
                    "environment": self.environment.environment_id,
                    "seed": seed,
                    "agents": list(self.environment.agents),
                },
            )
            done = False
            while not done:
                turn += 1
                actions: dict[str, Action] = {}
                telemetry: dict[str, dict[str, Any]] = {}

                for agent_id in self.environment.agents:
                    started = time.perf_counter()
                    error: str | None = None
                    try:
                        action = self.agents[agent_id].act(observations[agent_id])
                        if not isinstance(action, Action):
                            raise TypeError("agent must return Action")
                    except Exception as exc:  # runner boundary must contain agent failures
                        agent_errors[agent_id] += 1
                        action = Action(self.fallback_action)
                        error = f"{type(exc).__name__}: {exc}"
                    actions[agent_id] = action
                    telemetry[agent_id] = {
                        "latency_ms": round((time.perf_counter() - started) * 1000, 3),
                        "error": error,
                    }

                result = self.environment.step(actions)
                for agent_id in result.info.get("invalid_actions", []):
                    invalid_actions[agent_id] += 1

                self._write(
                    handle,
                    {
                        "schema_version": "arena.trace/v0",
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
                environment=self.environment.environment_id,
                seed=seed,
                winner=winner,
                turns=turn,
                scores=scores,
                invalid_actions=invalid_actions,
                agent_errors=agent_errors,
            )
            self._write(
                handle,
                {
                    "schema_version": "arena.trace/v0",
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
    def _write(handle: TextIO | None, record: Mapping[str, Any]) -> None:
        if handle is not None:
            handle.write(json.dumps(record, ensure_ascii=False, separators=(",", ":")) + "\n")
            handle.flush()
