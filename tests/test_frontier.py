from __future__ import annotations

import json

from open_agent_arena.agents import GreedyFrontierAgent, RandomAgent
from open_agent_arena.core import Action
from open_agent_arena.environments import FrontierEnvironment
from open_agent_arena.runner import MatchRunner


def run_reference(seed: int):
    return MatchRunner(
        FrontierEnvironment(max_turns=9),
        {"red": GreedyFrontierAgent(), "blue": RandomAgent(seed=42)},
    ).run(seed=seed)


def test_same_seed_reproduces_scores() -> None:
    first = run_reference(7)
    second = run_reference(7)
    assert first.scores == second.scores
    assert first.winner == second.winner
    assert first.turns == second.turns


def test_trace_has_one_record_per_transition(tmp_path) -> None:
    log_path = tmp_path / "match.jsonl"
    summary = MatchRunner(
        FrontierEnvironment(max_turns=4),
        {"red": GreedyFrontierAgent(), "blue": RandomAgent(seed=1)},
    ).run(seed=3, log_path=log_path)

    records = [json.loads(line) for line in log_path.read_text().splitlines()]
    assert records[0]["type"] == "match_started"
    assert records[-1]["type"] == "match_finished"
    assert len([record for record in records if record["type"] == "step"]) == summary.turns


def test_invalid_action_is_contained_and_counted() -> None:
    class BrokenAgent:
        def act(self, observation):
            return Action("read_hidden_server_state")

    summary = MatchRunner(
        FrontierEnvironment(max_turns=2),
        {"red": BrokenAgent(), "blue": GreedyFrontierAgent()},
    ).run(seed=0)
    assert summary.invalid_actions["red"] == 2
    assert summary.agent_errors["red"] == 0


def test_private_observations_are_recipient_specific() -> None:
    observations = FrontierEnvironment().reset(seed=0)
    assert observations["red"].agent_id == "red"
    assert observations["blue"].agent_id == "blue"
    assert observations["red"] is not observations["blue"]
