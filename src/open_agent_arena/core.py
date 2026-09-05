"""Transport-independent contracts between agents, runners, and environments."""

from __future__ import annotations

import json
import math
from collections.abc import Mapping
from dataclasses import dataclass, field
from typing import Any, Protocol, runtime_checkable

JsonObject = Mapping[str, Any]


@dataclass(frozen=True, slots=True)
class Action:
    """A structured command submitted by an agent."""

    kind: str
    payload: JsonObject = field(default_factory=dict)

    def __post_init__(self) -> None:
        if not isinstance(self.kind, str) or not self.kind:
            raise ValueError("action kind must be a non-empty string")
        if not isinstance(self.payload, Mapping):
            raise TypeError("action payload must be a mapping")
        _require_json(self.payload, "action payload")


@dataclass(frozen=True, slots=True)
class AgentUsage:
    """Provider-agnostic resource usage incurred by one decision."""

    input_tokens: int = 0
    output_tokens: int = 0
    model_calls: int = 0
    tool_calls: int = 0
    cost_usd: float = 0.0

    def __post_init__(self) -> None:
        counts = (self.input_tokens, self.output_tokens, self.model_calls, self.tool_calls)
        if any(not isinstance(value, int) or value < 0 for value in counts):
            raise ValueError("token and call usage must be non-negative integers")
        if not math.isfinite(self.cost_usd) or self.cost_usd < 0:
            raise ValueError("cost_usd must be a finite, non-negative number")


@dataclass(frozen=True, slots=True)
class AgentDecision:
    """An action plus auditable usage reported by an agent adapter."""

    action: Action
    usage: AgentUsage = field(default_factory=AgentUsage)
    metadata: JsonObject = field(default_factory=dict)

    def __post_init__(self) -> None:
        if not isinstance(self.metadata, Mapping):
            raise TypeError("decision metadata must be a mapping")
        _require_json(self.metadata, "decision metadata")


@dataclass(frozen=True, slots=True)
class AgentBudget:
    """Per-match limits. ``None`` means that a dimension is not capped."""

    decision_timeout_ms: int = 10_000
    max_input_tokens: int | None = None
    max_output_tokens: int | None = None
    max_model_calls: int | None = None
    max_tool_calls: int | None = None
    max_cost_usd: float | None = None

    def __post_init__(self) -> None:
        if self.decision_timeout_ms <= 0:
            raise ValueError("decision_timeout_ms must be positive")
        count_limits = (
            self.max_input_tokens,
            self.max_output_tokens,
            self.max_model_calls,
            self.max_tool_calls,
        )
        if any(
            limit is not None and (not isinstance(limit, int) or limit < 0)
            for limit in count_limits
        ):
            raise ValueError("token and call budgets must be non-negative integers")
        if self.max_cost_usd is not None and (
            not math.isfinite(self.max_cost_usd) or self.max_cost_usd < 0
        ):
            raise ValueError("max_cost_usd must be finite and non-negative")


class AgentTimeoutError(TimeoutError):
    """An adapter-enforced decision deadline expired."""


@dataclass(frozen=True, slots=True)
class Observation:
    """The complete view an environment permits one agent to see."""

    agent_id: str
    turn: int
    max_turns: int
    public_state: JsonObject
    private_state: JsonObject
    legal_actions: tuple[str, ...]
    budget_remaining: JsonObject = field(default_factory=dict)


@dataclass(frozen=True, slots=True)
class StepResult:
    """One authoritative environment transition."""

    observations: Mapping[str, Observation]
    rewards: Mapping[str, float]
    terminated: bool
    truncated: bool
    info: JsonObject = field(default_factory=dict)


@runtime_checkable
class ArenaAgent(Protocol):
    """An agent may be local, model-backed, human, or a remote adapter."""

    def act(self, observation: Observation) -> Action | AgentDecision:
        """Return one action before the runner's deadline."""


@runtime_checkable
class ArenaEnvironment(Protocol):
    """An authoritative, versioned multi-agent state machine."""

    environment_id: str
    agents: tuple[str, ...]

    def reset(self, seed: int) -> Mapping[str, Observation]:
        """Start a new episode using only the supplied randomness seed."""

    def step(self, actions: Mapping[str, Action]) -> StepResult:
        """Validate actions and advance exactly one environment step."""

    def scores(self) -> Mapping[str, float]:
        """Return current comparable payoff for each agent."""


def _require_json(value: Any, label: str) -> None:
    try:
        json.dumps(value, allow_nan=False)
    except (TypeError, ValueError) as exc:
        raise ValueError(f"{label} must be JSON-serializable") from exc
