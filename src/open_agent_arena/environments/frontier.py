"""A tiny simultaneous-action strategy environment for protocol validation."""

from __future__ import annotations

import random
from copy import deepcopy
from typing import Any, Mapping

from ..core import Action, Observation, StepResult


class FrontierEnvironment:
    """Two frontier states balance food, forces, walls, and territorial pressure."""

    environment_id = "frontier-v0"
    agents = ("red", "blue")
    _costs = {"recruit": 3, "fortify": 2}

    def __init__(self, max_turns: int = 12) -> None:
        if max_turns < 1:
            raise ValueError("max_turns must be positive")
        self.max_turns = max_turns
        self._rng = random.Random()
        self._turn = 0
        self._players: dict[str, dict[str, int]] = {}
        self._last_event: str | None = None

    def reset(self, seed: int) -> Mapping[str, Observation]:
        self._rng.seed(seed)
        self._turn = 0
        self._last_event = None
        self._players = {
            agent_id: {"grain": 8, "troops": 4, "walls": 1, "territory": 3, "morale": 5}
            for agent_id in self.agents
        }
        return self._observations()

    def step(self, actions: Mapping[str, Action]) -> StepResult:
        if not self._players:
            raise RuntimeError("reset must be called before step")
        self._turn += 1
        rewards = {agent_id: 0.0 for agent_id in self.agents}
        invalid: list[str] = []
        normalized: dict[str, str] = {}

        for agent_id in self.agents:
            legal = self._legal_actions(agent_id)
            action = actions.get(agent_id, Action("idle"))
            if action.kind not in legal:
                invalid.append(agent_id)
                normalized[agent_id] = "idle"
                self._players[agent_id]["morale"] = max(
                    0, self._players[agent_id]["morale"] - 1
                )
                rewards[agent_id] -= 0.1
            else:
                normalized[agent_id] = action.kind

        start = deepcopy(self._players)
        for agent_id, kind in normalized.items():
            player = self._players[agent_id]
            if kind == "harvest":
                player["grain"] += 4
                rewards[agent_id] += 0.05
            elif kind == "recruit":
                player["grain"] -= self._costs["recruit"]
                player["troops"] += 2
            elif kind == "fortify":
                player["grain"] -= self._costs["fortify"]
                player["walls"] += 1

        attack_reports: list[dict[str, Any]] = []
        for attacker_id, kind in normalized.items():
            if kind != "attack":
                continue
            defender_id = self._opponent(attacker_id)
            committed = max(1, start[attacker_id]["troops"] // 2)
            attack_strength = committed + self._rng.randint(-1, 1)
            defense_strength = max(1, start[defender_id]["troops"] // 3) + (
                2 * start[defender_id]["walls"]
            )
            success = attack_strength > defense_strength
            attacker = self._players[attacker_id]
            defender = self._players[defender_id]
            attacker["troops"] = max(1, attacker["troops"] - max(1, committed // 2))
            if success and defender["territory"] > 0:
                defender["territory"] -= 1
                attacker["territory"] += 1
                defender["troops"] = max(1, defender["troops"] - 1)
                attacker["morale"] = min(10, attacker["morale"] + 1)
                rewards[attacker_id] += 1.0
                rewards[defender_id] -= 1.0
            else:
                attacker["morale"] = max(0, attacker["morale"] - 1)
                rewards[attacker_id] -= 0.2
            attack_reports.append(
                {
                    "attacker": attacker_id,
                    "defender": defender_id,
                    "attack_strength": attack_strength,
                    "defense_strength": defense_strength,
                    "success": success,
                }
            )

        self._last_event = self._apply_world_event() if self._turn % 3 == 0 else None
        terminated = any(player["territory"] == 0 for player in self._players.values())
        truncated = self._turn >= self.max_turns and not terminated
        return StepResult(
            observations=self._observations(),
            rewards=rewards,
            terminated=terminated,
            truncated=truncated,
            info={
                "invalid_actions": invalid,
                "normalized_actions": normalized,
                "attacks": attack_reports,
                "world_event": self._last_event,
            },
        )

    def scores(self) -> Mapping[str, float]:
        return {
            agent_id: round(
                player["territory"]
                + 0.1 * player["troops"]
                + 0.05 * player["grain"]
                + 0.02 * player["morale"],
                3,
            )
            for agent_id, player in self._players.items()
        }

    def _observations(self) -> Mapping[str, Observation]:
        public = {"players": deepcopy(self._players), "last_event": self._last_event}
        return {
            agent_id: Observation(
                agent_id=agent_id,
                turn=self._turn,
                max_turns=self.max_turns,
                public_state=deepcopy(public),
                private_state={"next_event_hint": self._event_hint(agent_id)},
                legal_actions=self._legal_actions(agent_id),
            )
            for agent_id in self.agents
        }

    def _legal_actions(self, agent_id: str) -> tuple[str, ...]:
        player = self._players[agent_id]
        actions = ["harvest"]
        if player["grain"] >= self._costs["recruit"]:
            actions.append("recruit")
        if player["grain"] >= self._costs["fortify"]:
            actions.append("fortify")
        if player["troops"] >= 2:
            actions.append("attack")
        return tuple(actions)

    def _apply_world_event(self) -> str:
        event = self._rng.choice(("drought", "good_harvest", "desertion"))
        for player in self._players.values():
            if event == "drought":
                player["grain"] = max(0, player["grain"] - 2)
            elif event == "good_harvest":
                player["grain"] += 2
            else:
                player["troops"] = max(1, player["troops"] - 1)
        return event

    def _event_hint(self, agent_id: str) -> str | None:
        # Different noisy hints exercise recipient-specific observations.
        if (self._turn + (0 if agent_id == "red" else 1)) % 3 == 2:
            return "weather may shift next turn"
        return None

    def _opponent(self, agent_id: str) -> str:
        return "blue" if agent_id == "red" else "red"
