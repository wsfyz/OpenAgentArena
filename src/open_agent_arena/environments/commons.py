"""A three-agent social dilemma with partial observability and shared risk."""

from __future__ import annotations

import random
from collections.abc import Mapping
from copy import deepcopy

from ..core import Action, Observation, StepResult


class CommonsEnvironment:
    """Agents balance private reserves against the survival of a shared commons."""

    environment_id = "commons-v0"
    agents = ("cedar", "moss", "river")

    def __init__(self, max_turns: int = 9) -> None:
        if max_turns < 1:
            raise ValueError("max_turns must be positive")
        self.max_turns = max_turns
        self._rng = random.Random()
        self._turn = 0
        self._common = 0.0
        self._players: dict[str, dict[str, float]] = {}
        self._signals: dict[str, str | None] = {}
        self._last_event: str | None = None
        self._collapsed = False

    def reset(self, seed: int) -> Mapping[str, Observation]:
        self._rng.seed(seed)
        self._turn = 0
        self._common = 18.0
        self._players = {
            agent_id: {"reserve": 5.0, "reputation": 0.0}
            for agent_id in self.agents
        }
        self._signals = {agent_id: None for agent_id in self.agents}
        self._last_event = None
        self._collapsed = False
        return self._observations()

    def step(self, actions: Mapping[str, Action]) -> StepResult:
        if not self._players:
            raise RuntimeError("reset must be called before step")
        if self._collapsed or self._turn >= self.max_turns:
            raise RuntimeError("episode is already complete")
        self._turn += 1
        rewards = {agent_id: 0.0 for agent_id in self.agents}
        invalid: list[str] = []
        normalized: dict[str, str] = {}
        for agent_id in self.agents:
            action = actions.get(agent_id, Action("idle"))
            if action.kind not in self._legal_actions(agent_id):
                invalid.append(agent_id)
                normalized[agent_id] = "idle"
                rewards[agent_id] -= 0.1
            else:
                normalized[agent_id] = action.kind

        harvesters = [agent_id for agent_id, kind in normalized.items() if kind == "harvest"]
        total_harvest = min(self._common, 3.0 * len(harvesters))
        harvest_share = total_harvest / len(harvesters) if harvesters else 0.0
        self._common -= total_harvest
        for agent_id in harvesters:
            self._players[agent_id]["reserve"] += harvest_share
            self._players[agent_id]["reputation"] -= 0.25
            rewards[agent_id] += harvest_share * 0.1

        contributions = 0.0
        guards = 0
        next_signals = {agent_id: None for agent_id in self.agents}
        for agent_id, kind in normalized.items():
            player = self._players[agent_id]
            if kind == "contribute":
                player["reserve"] -= 1.0
                player["reputation"] += 1.0
                contributions += 2.5
                rewards[agent_id] += 0.2
            elif kind == "guard":
                player["reserve"] -= 1.0
                player["reputation"] += 0.5
                guards += 1
                rewards[agent_id] += 0.1
            elif kind == "observe":
                player["reserve"] -= 0.5
                others = sum(
                    state["reserve"]
                    for other_id, state in self._players.items()
                    if other_id != agent_id
                )
                noisy_total = max(0, round(others + self._rng.uniform(-1.0, 1.0), 1))
                next_signals[agent_id] = f"others hold about {noisy_total} reserve"
        self._signals = next_signals
        self._common += contributions

        self._last_event = None
        if self._turn % 3 == 0:
            shock = max(0.0, 6.0 - 2.0 * guards)
            self._common = max(0.0, self._common - shock)
            self._last_event = f"storm consumed {shock:.1f} commons"
        else:
            self._common = min(30.0, self._common + 1.0)

        self._collapsed = self._common <= 0
        if self._collapsed:
            for agent_id in self.agents:
                rewards[agent_id] -= 2.0
        terminated = self._collapsed
        truncated = self._turn >= self.max_turns and not terminated
        return StepResult(
            observations=self._observations(),
            rewards=rewards,
            terminated=terminated,
            truncated=truncated,
            info={
                "invalid_actions": invalid,
                "normalized_actions": normalized,
                "total_harvest": total_harvest,
                "total_contribution": contributions,
                "guards": guards,
                "world_event": self._last_event,
                "commons_collapsed": self._collapsed,
            },
        )

    def scores(self) -> Mapping[str, float]:
        survival_bonus = 5.0 if not self._collapsed and self._turn >= self.max_turns else 0.0
        shared_value = self._common / len(self.agents)
        return {
            agent_id: round(
                player["reserve"]
                + 0.5 * player["reputation"]
                + 0.2 * shared_value
                + survival_bonus,
                3,
            )
            for agent_id, player in self._players.items()
        }

    def _observations(self) -> Mapping[str, Observation]:
        public = {
            "commons": round(self._common, 3),
            "reputations": {
                agent_id: round(player["reputation"], 3)
                for agent_id, player in self._players.items()
            },
            "last_event": self._last_event,
        }
        return {
            agent_id: Observation(
                agent_id=agent_id,
                turn=self._turn,
                max_turns=self.max_turns,
                public_state=deepcopy(public),
                private_state={
                    "reserve": round(self._players[agent_id]["reserve"], 3),
                    "market_signal": self._signals[agent_id],
                },
                legal_actions=self._legal_actions(agent_id),
            )
            for agent_id in self.agents
        }

    def _legal_actions(self, agent_id: str) -> tuple[str, ...]:
        actions = ["harvest"]
        reserve = self._players[agent_id]["reserve"]
        if reserve >= 1.0:
            actions.extend(("contribute", "guard"))
        if reserve >= 0.5:
            actions.append("observe")
        return tuple(actions)
