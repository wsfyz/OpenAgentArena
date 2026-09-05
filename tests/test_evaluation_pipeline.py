from __future__ import annotations

import json
import sys
from pathlib import Path

from open_agent_arena.agents import (
    GreedyFrontierAgent,
    OpenAICompatibleAgent,
    RandomAgent,
    SubprocessAgent,
)
from open_agent_arena.core import (
    Action,
    AgentBudget,
    AgentDecision,
    AgentTimeoutError,
    AgentUsage,
)
from open_agent_arena.environments import FrontierEnvironment
from open_agent_arena.replay import verify_trace
from open_agent_arena.reporting import write_leaderboard_html, write_replay_html
from open_agent_arena.runner import MatchRunner
from open_agent_arena.tournament import TournamentRunner


class MeteredAgent:
    def __init__(self) -> None:
        self.remaining: list[int | None] = []

    def act(self, observation):
        self.remaining.append(observation.budget_remaining["input_tokens"])
        return AgentDecision(
            Action("harvest"),
            AgentUsage(input_tokens=2, output_tokens=1, model_calls=1, cost_usd=0.01),
        )


def test_runner_records_usage_and_enforces_budget(tmp_path: Path) -> None:
    metered = MeteredAgent()
    trace = tmp_path / "metered.jsonl"
    summary = MatchRunner(
        FrontierEnvironment(max_turns=3),
        {"red": metered, "blue": GreedyFrontierAgent()},
        budgets=AgentBudget(max_input_tokens=3),
    ).run(seed=4, log_path=trace)

    assert metered.remaining == [3, 1]
    assert summary.telemetry["red"]["input_tokens"] == 4
    assert summary.telemetry["red"]["budget_exhaustions"] == 2
    records = [json.loads(line) for line in trace.read_text().splitlines()]
    assert records[0]["schema_version"] == "arena.trace/v1"
    assert records[2]["telemetry"]["red"]["budget_exhausted"] is True


def test_negative_usage_is_rejected() -> None:
    try:
        AgentUsage(input_tokens=-1)
    except ValueError as exc:
        assert "non-negative" in str(exc)
    else:
        raise AssertionError("negative usage must not be accepted")


def test_adapter_timeout_is_counted_separately() -> None:
    class TimeoutAgent:
        def act(self, observation):
            raise AgentTimeoutError("provider deadline")

    summary = MatchRunner(
        FrontierEnvironment(max_turns=2),
        {"red": TimeoutAgent(), "blue": GreedyFrontierAgent()},
    ).run(seed=0)
    assert summary.telemetry["red"]["timeouts"] == 2
    assert summary.agent_errors["red"] == 0


def test_tournament_swaps_seats_and_writes_artifacts(tmp_path: Path) -> None:
    summary = TournamentRunner(
        lambda: FrontierEnvironment(max_turns=4),
        {
            "greedy": lambda seed: GreedyFrontierAgent(),
            "random": lambda seed: RandomAgent(seed),
        },
    ).run(seeds=(1, 2), output_dir=tmp_path)

    assert len(summary.matches) == 4
    assert summary.matches[0].seats != summary.matches[1].seats
    assert {standing["played"] for standing in summary.standings} == {4}
    assert (tmp_path / "tournament.json").exists()
    report = write_leaderboard_html(summary, tmp_path / "leaderboard.html")
    assert "Tournament leaderboard" in report.read_text()


def test_replay_verifier_detects_tampering(tmp_path: Path) -> None:
    trace = tmp_path / "match.jsonl"
    MatchRunner(
        FrontierEnvironment(max_turns=4),
        {"red": GreedyFrontierAgent(), "blue": RandomAgent(2)},
    ).run(seed=3, log_path=trace)
    factory = lambda: FrontierEnvironment(max_turns=4)  # noqa: E731

    assert verify_trace(trace, factory).valid is True
    records = [json.loads(line) for line in trace.read_text().splitlines()]
    records[1]["rewards"]["red"] = 999
    trace.write_text("\n".join(json.dumps(record) for record in records) + "\n")
    verification = verify_trace(trace, factory)
    assert verification.valid is False
    assert "turn 1: rewards mismatch" in verification.errors


def test_static_replay_is_generated(tmp_path: Path) -> None:
    trace = tmp_path / "match.jsonl"
    MatchRunner(
        FrontierEnvironment(max_turns=2),
        {"red": GreedyFrontierAgent(), "blue": RandomAgent(2)},
    ).run(seed=3, log_path=trace)
    replay = write_replay_html(trace, tmp_path / "replay.html")
    assert "TRACE REPLAY" in replay.read_text()


def test_subprocess_agent_uses_json_contract() -> None:
    script = (
        "import json,sys; request=json.load(sys.stdin); "
        "assert request['schema_version']=='arena.agent-request/v1'; "
        "json.dump({'action':{'kind':'harvest'},"
        "'usage':{'tool_calls':2}},sys.stdout)"
    )
    agent = SubprocessAgent((sys.executable, "-c", script))
    observation = FrontierEnvironment(max_turns=1).reset(seed=0)["red"]
    decision = agent.act(observation)
    assert decision.action == Action("harvest")
    assert decision.usage.tool_calls == 2


def test_openai_compatible_adapter_reports_usage(monkeypatch) -> None:
    class FakeResponse:
        def __enter__(self):
            return self

        def __exit__(self, *args):
            return None

        def read(self):
            return json.dumps(
                {
                    "id": "req-1",
                    "model": "test-model",
                    "choices": [{"message": {"content": '{"kind":"harvest"}'}}],
                    "usage": {"prompt_tokens": 100, "completion_tokens": 20},
                }
            ).encode()

    monkeypatch.setattr(
        "open_agent_arena.agents.adapters.request.urlopen",
        lambda req, timeout: FakeResponse(),
    )
    agent = OpenAICompatibleAgent(
        model="test-model",
        base_url="https://models.invalid/v1",
        input_cost_per_million=2.0,
        output_cost_per_million=4.0,
    )
    observation = FrontierEnvironment(max_turns=1).reset(seed=0)["red"]
    decision = agent.act(observation)
    assert decision.action == Action("harvest")
    assert decision.usage.input_tokens == 100
    assert decision.usage.cost_usd == 0.00028
