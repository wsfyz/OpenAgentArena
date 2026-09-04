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
