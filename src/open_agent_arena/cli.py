"""Command-line workflows for matches, tournaments, verification, and replay."""

from __future__ import annotations

import argparse
import json
from collections.abc import Callable
from dataclasses import asdict

from .agents import (
    CommonsCooperatorAgent,
    CommonsFreeRiderAgent,
    GreedyFrontierAgent,
    RandomAgent,
)
from .battle import load_battle_config, missing_api_keys, run_base_model_battle
from .core import AgentBudget, ArenaAgent
from .environments import CommonsEnvironment, FrontierEnvironment
from .replay import read_trace, verify_trace
from .reporting import write_leaderboard_html, write_replay_html
from .runner import MatchRunner
from .tournament import TournamentRunner


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Run and evaluate OpenAgentArena agents")
    subparsers = parser.add_subparsers(dest="command", required=True)

    run = subparsers.add_parser("run", help="run one bundled frontier-v0 match")
    run.add_argument("--seed", type=int, default=7)
    run.add_argument("--max-turns", type=int, default=12)
    run.add_argument("--red", choices=("greedy", "random"), default="greedy")
    run.add_argument("--blue", choices=("greedy", "random"), default="random")
    run.add_argument("--log", default="runs/demo.jsonl")
    _add_budget_arguments(run)

    commons = subparsers.add_parser("commons", help="run one three-agent commons-v0 match")
    commons.add_argument("--seed", type=int, default=7)
    commons.add_argument("--max-turns", type=int, default=9)
    commons.add_argument("--log", default="runs/commons.jsonl")
    _add_budget_arguments(commons)

    tournament = subparsers.add_parser(
        "tournament", help="run paired-seed, seat-swapped baseline matches"
    )
    tournament.add_argument("--seeds", default="1,2,3,4,5")
    tournament.add_argument("--max-turns", type=int, default=12)
    tournament.add_argument("--output-dir", default="runs/tournament")
    _add_budget_arguments(tournament)

    verify = subparsers.add_parser("verify", help="replay and verify a JSONL trace")
    verify.add_argument("trace")
    verify.add_argument("--max-turns", type=int, default=12)

    replay = subparsers.add_parser("replay", help="generate a static replay viewer")
    replay.add_argument("trace")
    replay.add_argument("--output", default="runs/replay.html")

    battle = subparsers.add_parser(
        "battle", help="compare two API models with one controlled agent template"
    )
    battle.add_argument("config", help="path to a version 1 TOML battle config")
    battle.add_argument(
        "--check", action="store_true", help="validate config and API key presence only"
    )
    return parser


def _add_budget_arguments(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("--decision-timeout-ms", type=int, default=10_000)
    parser.add_argument("--max-input-tokens", type=int)
    parser.add_argument("--max-output-tokens", type=int)
    parser.add_argument("--max-tool-calls", type=int)
    parser.add_argument("--max-model-calls", type=int)
    parser.add_argument("--max-cost-usd", type=float)


def _budget(args: argparse.Namespace) -> AgentBudget:
    return AgentBudget(
        decision_timeout_ms=args.decision_timeout_ms,
        max_input_tokens=args.max_input_tokens,
        max_output_tokens=args.max_output_tokens,
        max_tool_calls=args.max_tool_calls,
        max_model_calls=args.max_model_calls,
        max_cost_usd=args.max_cost_usd,
    )


def _factory(name: str) -> Callable[[int], ArenaAgent]:
    if name == "greedy":
        return lambda seed: GreedyFrontierAgent()
    if name == "random":
        return lambda seed: RandomAgent(seed=seed)
    raise ValueError(f"unknown built-in agent: {name}")


def _parse_seeds(raw: str) -> tuple[int, ...]:
    try:
        seeds = tuple(int(item.strip()) for item in raw.split(",") if item.strip())
    except ValueError as exc:
        raise argparse.ArgumentTypeError("seeds must be comma-separated integers") from exc
    if not seeds:
        raise argparse.ArgumentTypeError("at least one seed is required")
    return seeds


def _trace_environment(trace: str, max_turns: int):
    records = read_trace(trace)
    if not records:
        raise ValueError("trace is empty")
    environment_id = records[0].get("environment")
    if environment_id == "frontier-v0":
        return lambda: FrontierEnvironment(max_turns=max_turns)
    if environment_id == "commons-v0":
        return lambda: CommonsEnvironment(max_turns=max_turns)
    raise ValueError(f"unsupported trace environment: {environment_id}")


def main() -> None:
    args = build_parser().parse_args()
    if args.command == "run":
        runner = MatchRunner(
            FrontierEnvironment(max_turns=args.max_turns),
            {
                "red": _factory(args.red)(args.seed),
                "blue": _factory(args.blue)(args.seed + 1),
            },
            budgets=_budget(args),
        )
        summary = runner.run(seed=args.seed, log_path=args.log)
        print(json.dumps(asdict(summary), ensure_ascii=False, indent=2))
    elif args.command == "commons":
        runner = MatchRunner(
            CommonsEnvironment(max_turns=args.max_turns),
            {
                "cedar": CommonsCooperatorAgent(),
                "moss": CommonsFreeRiderAgent(),
                "river": CommonsCooperatorAgent(),
            },
            budgets=_budget(args),
        )
        summary = runner.run(seed=args.seed, log_path=args.log)
        print(json.dumps(asdict(summary), ensure_ascii=False, indent=2))
    elif args.command == "tournament":
        seeds = _parse_seeds(args.seeds)
        runner = TournamentRunner(
            lambda: FrontierEnvironment(max_turns=args.max_turns),
            {"greedy": _factory("greedy"), "random": _factory("random")},
            budgets=_budget(args),
        )
        summary = runner.run(seeds=seeds, output_dir=args.output_dir)
        report_path = write_leaderboard_html(
            summary, f"{args.output_dir}/leaderboard.html"
        )
        print(
            json.dumps(
                {"standings": summary.standings, "report": str(report_path)},
                ensure_ascii=False,
                indent=2,
            )
        )
    elif args.command == "verify":
        verification = verify_trace(args.trace, _trace_environment(args.trace, args.max_turns))
        print(json.dumps(asdict(verification), ensure_ascii=False, indent=2))
        if not verification.valid:
            raise SystemExit(1)
    elif args.command == "replay":
        output = write_replay_html(args.trace, args.output)
        print(json.dumps({"replay": str(output)}, ensure_ascii=False, indent=2))
    elif args.command == "battle":
        config = load_battle_config(args.config)
        missing = missing_api_keys(config)
        if args.check:
            print(
                json.dumps(
                    {
                        "valid": not missing,
                        "battle": config.name,
                        "models": [model.name for model in config.models],
                        "games": len(config.seeds) * 2,
                        "missing_api_keys": missing,
                    },
                    ensure_ascii=False,
                    indent=2,
                )
            )
            if missing:
                raise SystemExit(2)
        else:
            summary, report = run_base_model_battle(config)
            print(
                json.dumps(
                    {"standings": summary.standings, "report": str(report)},
                    ensure_ascii=False,
                    indent=2,
                )
            )


if __name__ == "__main__":
    main()
