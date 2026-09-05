"""Simple baselines; useful benchmarks need agents weaker than the target systems."""

from __future__ import annotations

import random

from ..core import Action, Observation


class RandomAgent:
    def __init__(self, seed: int = 0) -> None:
        self._rng = random.Random(seed)

    def act(self, observation: Observation) -> Action:
        return Action(self._rng.choice(observation.legal_actions))


class GreedyFrontierAgent:
    """A transparent reference policy for the bundled frontier environment."""

    def act(self, observation: Observation) -> Action:
        world = observation.public_state["players"]
        own = world[observation.agent_id]
        opponent_id = next(agent_id for agent_id in world if agent_id != observation.agent_id)
        opponent = world[opponent_id]
        legal = observation.legal_actions

        if "attack" in legal and own["troops"] >= opponent["troops"] + opponent["walls"]:
            return Action("attack")
        if "recruit" in legal and own["troops"] <= opponent["troops"] + 2:
            return Action("recruit")
        if "fortify" in legal and own["walls"] < 3:
            return Action("fortify")
        return Action("harvest")


class CommonsCooperatorAgent:
    """Protect the shared resource while maintaining a small private reserve."""

    def act(self, observation: Observation) -> Action:
        commons = observation.public_state["commons"]
        reserve = observation.private_state["reserve"]
        turns_until_storm = (3 - observation.turn % 3) % 3
        if turns_until_storm == 1 and "guard" in observation.legal_actions:
            return Action("guard")
        if commons < 16 and reserve >= 2 and "contribute" in observation.legal_actions:
            return Action("contribute")
        if reserve < 3:
            return Action("harvest")
        return Action("observe")


class CommonsFreeRiderAgent:
    """Maximize immediate private extraction from the shared resource."""

    def act(self, observation: Observation) -> Action:
        return Action("harvest")
