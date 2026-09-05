"""Offline verification of immutable match traces."""

from __future__ import annotations

import hashlib
import json
from collections.abc import Callable, Mapping
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

from .core import Action, ArenaEnvironment
from .runner import MatchRunner


@dataclass(frozen=True, slots=True)
class ReplayVerification:
    valid: bool
    trace_digest: str
    match_id: str | None
    turns: int
    errors: tuple[str, ...]


def read_trace(path: str | Path) -> list[dict[str, Any]]:
    records: list[dict[str, Any]] = []
    for line_number, line in enumerate(Path(path).read_text(encoding="utf-8").splitlines(), 1):
        try:
            records.append(json.loads(line))
        except json.JSONDecodeError as exc:
            raise ValueError(f"invalid JSON on line {line_number}: {exc}") from exc
    return records


def verify_trace(
    path: str | Path,
    environment_factory: Callable[[], ArenaEnvironment],
) -> ReplayVerification:
    trace_path = Path(path)
    digest = hashlib.sha256(trace_path.read_bytes()).hexdigest()
    errors: list[str] = []
    try:
        records = read_trace(trace_path)
    except ValueError as exc:
        return ReplayVerification(False, digest, None, 0, (str(exc),))
    if len(records) < 2:
        return ReplayVerification(False, digest, None, 0, ("trace is incomplete",))

    started, finished = records[0], records[-1]
    match_id = started.get("match_id")
    if started.get("type") != "match_started":
        errors.append("first record must be match_started")
    if finished.get("type") != "match_finished":
        errors.append("last record must be match_finished")
    environment = environment_factory()
    if started.get("environment") != environment.environment_id:
        errors.append("environment id does not match verifier")
    observations = environment.reset(int(started.get("seed", 0)))
    steps = [record for record in records[1:-1] if record.get("type") == "step"]

    for expected_turn, record in enumerate(steps, 1):
        if record.get("match_id") != match_id:
            errors.append(f"turn {expected_turn}: match id mismatch")
        if record.get("turn") != expected_turn:
            errors.append(f"turn {expected_turn}: non-contiguous turn number")
        if not _same(record.get("observations"), _observations_dict(observations)):
            errors.append(f"turn {expected_turn}: observation mismatch")
        actions = {
            agent_id: Action(
                kind=value["kind"],
                payload=value.get("payload", {}),
            )
            for agent_id, value in record.get("actions", {}).items()
        }
        try:
            result = environment.step(actions)
        except Exception as exc:  # verifier must report malformed traces, not crash
            errors.append(f"turn {expected_turn}: environment rejected action: {exc}")
            break
        checks = {
            "rewards": dict(result.rewards),
            "terminated": result.terminated,
            "truncated": result.truncated,
            "info": dict(result.info),
        }
        for field, expected in checks.items():
            if not _same(record.get(field), expected):
                errors.append(f"turn {expected_turn}: {field} mismatch")
        observations = result.observations

    scores = dict(environment.scores())
    if not _same(finished.get("scores"), scores):
        errors.append("final score mismatch")
    if finished.get("winner") != MatchRunner._winner(scores):
        errors.append("winner mismatch")
    if finished.get("turns") != len(steps):
        errors.append("finished turn count mismatch")
    return ReplayVerification(not errors, digest, match_id, len(steps), tuple(errors))


def _observations_dict(observations: Mapping[str, Any]) -> dict[str, Any]:
    return {agent_id: asdict(observation) for agent_id, observation in observations.items()}


def _same(left: Any, right: Any) -> bool:
    return json.dumps(left, sort_keys=True, separators=(",", ":")) == json.dumps(
        right, sort_keys=True, separators=(",", ":")
    )
