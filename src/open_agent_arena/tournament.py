"""Paired-seed, seat-swapped round-robin tournament orchestration."""

from __future__ import annotations

import json
from collections.abc import Callable, Mapping, Sequence
from dataclasses import asdict, dataclass
from itertools import combinations
from pathlib import Path

from .core import AgentBudget, ArenaAgent, ArenaEnvironment
from .runner import MatchRunner, MatchSummary

AgentFactory = Callable[[int], ArenaAgent]
EnvironmentFactory = Callable[[], ArenaEnvironment]


@dataclass(frozen=True, slots=True)
class TournamentMatch:
    match_id: str
    seed: int
    seats: Mapping[str, str]
    winner: str | None
    scores: Mapping[str, float]
    trace_path: str
    summary: MatchSummary


@dataclass(slots=True)
class Standing:
    name: str
    rating: float = 1500.0
    played: int = 0
    wins: int = 0
    draws: int = 0
    losses: int = 0
    score_for: float = 0.0
    score_against: float = 0.0
    cost_usd: float = 0.0
    input_tokens: int = 0
    output_tokens: int = 0
    tool_calls: int = 0
    errors: int = 0

    @property
    def points(self) -> float:
        return self.wins + 0.5 * self.draws

    def public(self) -> dict[str, int | float | str]:
        data = asdict(self)
        data["rating"] = round(self.rating, 2)
        data["points"] = self.points
        data["score_difference"] = round(self.score_for - self.score_against, 3)
        data["cost_usd"] = round(self.cost_usd, 8)
        return data


@dataclass(frozen=True, slots=True)
class TournamentSummary:
    environment: str
    seeds: tuple[int, ...]
    matches: tuple[TournamentMatch, ...]
    standings: tuple[Mapping[str, int | float | str], ...]

    def to_dict(self) -> dict[str, object]:
        return asdict(self)


class TournamentRunner:
    """Run every competitor pair on the same seeds in both seat orientations."""

    def __init__(
        self,
        environment_factory: EnvironmentFactory,
        competitors: Mapping[str, AgentFactory],
        *,
        budgets: Mapping[str, AgentBudget] | AgentBudget | None = None,
        elo_k: float = 24.0,
    ) -> None:
        if len(competitors) < 2:
            raise ValueError("a tournament requires at least two competitors")
        if elo_k <= 0:
            raise ValueError("elo_k must be positive")
        self.environment_factory = environment_factory
        self.competitors = dict(competitors)
        self.budgets = budgets
        self.elo_k = elo_k

    def run(
        self,
        *,
        seeds: Sequence[int],
        output_dir: str | Path,
    ) -> TournamentSummary:
        if not seeds:
            raise ValueError("at least one seed is required")
        root = Path(output_dir)
        traces_dir = root / "traces"
        traces_dir.mkdir(parents=True, exist_ok=True)
        standings = {name: Standing(name=name) for name in self.competitors}
        matches: list[TournamentMatch] = []
        environment_id: str | None = None

        for left, right in combinations(self.competitors, 2):
            for seed in seeds:
                for game_index, ordered in enumerate(((left, right), (right, left))):
                    environment = self.environment_factory()
                    environment_id = environment.environment_id
                    if len(environment.agents) != 2:
                        raise ValueError("v0 tournament runner requires exactly two seats")
                    seats = dict(zip(environment.agents, ordered, strict=True))
                    agents = {
                        seat: self.competitors[name](self._agent_seed(seed, name))
                        for seat, name in seats.items()
                    }
                    trace_name = f"{left}-vs-{right}-seed-{seed}-game-{game_index + 1}.jsonl"
                    trace_path = traces_dir / trace_name
                    summary = MatchRunner(
                        environment,
                        agents,
                        budgets=self.budgets,
                    ).run(seed=seed, log_path=trace_path)
                    winner = seats[summary.winner] if summary.winner is not None else None
                    named_scores = {
                        seats[seat]: score for seat, score in summary.scores.items()
                    }
                    match = TournamentMatch(
                        match_id=summary.match_id,
                        seed=seed,
                        seats=seats,
                        winner=winner,
                        scores=named_scores,
                        trace_path=str(trace_path),
                        summary=summary,
                    )
                    matches.append(match)
                    self._record_result(standings, match)

        ordered_standings = tuple(
            standing.public()
            for standing in sorted(
                standings.values(),
                key=lambda item: (item.rating, item.points, item.score_for),
                reverse=True,
            )
        )
        result = TournamentSummary(
            environment=environment_id or "unknown",
            seeds=tuple(seeds),
            matches=tuple(matches),
            standings=ordered_standings,
        )
        (root / "tournament.json").write_text(
            json.dumps(result.to_dict(), ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
        return result

    def _record_result(
        self, standings: Mapping[str, Standing], match: TournamentMatch
    ) -> None:
        names = list(match.seats.values())
        left, right = names[0], names[1]
        left_standing, right_standing = standings[left], standings[right]
        if match.winner is None:
            left_result = right_result = 0.5
            left_standing.draws += 1
            right_standing.draws += 1
        elif match.winner == left:
            left_result, right_result = 1.0, 0.0
            left_standing.wins += 1
            right_standing.losses += 1
        else:
            left_result, right_result = 0.0, 1.0
            left_standing.losses += 1
            right_standing.wins += 1

        rating_gap = right_standing.rating - left_standing.rating
        left_expected = 1.0 / (1.0 + 10 ** (rating_gap / 400))
        right_expected = 1.0 - left_expected
        left_standing.rating += self.elo_k * (left_result - left_expected)
        right_standing.rating += self.elo_k * (right_result - right_expected)

        for seat, name in match.seats.items():
            standing = standings[name]
            opponent_seat = next(other for other in match.seats if other != seat)
            standing.played += 1
            standing.score_for += match.summary.scores[seat]
            standing.score_against += match.summary.scores[opponent_seat]
            standing.errors += match.summary.agent_errors[seat]
            telemetry = match.summary.telemetry[seat]
            standing.input_tokens += int(telemetry["input_tokens"])
            standing.output_tokens += int(telemetry["output_tokens"])
            standing.tool_calls += int(telemetry["tool_calls"])
            standing.cost_usd += float(telemetry["cost_usd"])

    @staticmethod
    def _agent_seed(seed: int, name: str) -> int:
        name_value = sum((index + 1) * ord(char) for index, char in enumerate(name))
        return seed * 10_007 + name_value
