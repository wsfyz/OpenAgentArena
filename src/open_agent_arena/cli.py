"""Command-line entry point for the reference match."""

from __future__ import annotations

import argparse
import json
from dataclasses import asdict

from .agents import GreedyFrontierAgent, RandomAgent
from .environments import FrontierEnvironment
from .runner import MatchRunner


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Run an OpenAgentArena reference match")
    subparsers = parser.add_subparsers(dest="command", required=True)
    run = subparsers.add_parser("run", help="run the bundled frontier-v0 match")
    run.add_argument("--seed", type=int, default=7)
    run.add_argument("--max-turns", type=int, default=12)
    run.add_argument("--log", default="runs/demo.jsonl")
    return parser


def main() -> None:
    args = build_parser().parse_args()
    if args.command == "run":
        runner = MatchRunner(
            FrontierEnvironment(max_turns=args.max_turns),
            {"red": GreedyFrontierAgent(), "blue": RandomAgent(seed=args.seed + 1)},
        )
        summary = runner.run(seed=args.seed, log_path=args.log)
        print(json.dumps(asdict(summary), ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
