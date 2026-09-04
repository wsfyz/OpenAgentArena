"""Transport-independent contracts between agents, runners, and environments."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Mapping, Protocol, runtime_checkable

JsonObject = Mapping[str, Any]


@dataclass(frozen=True, slots=True)
class Action:
    """A structured command submitted by an agent."""

    kind: str
    payload: JsonObject = field(default_factory=dict)


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

    def act(self, observation: Observation) -> Action:
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
