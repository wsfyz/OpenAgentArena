from __future__ import annotations

from open_agent_arena.agents import CommonsCooperatorAgent, CommonsFreeRiderAgent
from open_agent_arena.environments import CommonsEnvironment
from open_agent_arena.replay import verify_trace
from open_agent_arena.runner import MatchRunner


def _agents():
    return {
        "cedar": CommonsCooperatorAgent(),
        "moss": CommonsFreeRiderAgent(),
        "river": CommonsCooperatorAgent(),
    }


def test_commons_is_deterministic_and_hides_private_reserves() -> None:
    first = MatchRunner(CommonsEnvironment(max_turns=6), _agents()).run(seed=8)
    second = MatchRunner(CommonsEnvironment(max_turns=6), _agents()).run(seed=8)
    assert first.scores == second.scores
    observations = CommonsEnvironment().reset(seed=0)
    assert "reserve" not in observations["cedar"].public_state
    assert "reserve" in observations["cedar"].private_state


def test_three_agent_trace_replays(tmp_path) -> None:
    trace = tmp_path / "commons.jsonl"
    MatchRunner(CommonsEnvironment(max_turns=6), _agents()).run(seed=5, log_path=trace)
    verification = verify_trace(trace, lambda: CommonsEnvironment(max_turns=6))
    assert verification.valid is True
