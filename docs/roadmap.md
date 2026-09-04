# Roadmap

Dates are intentionally relative. The project should advance when evidence gates pass, not when a feature list is exhausted.

## Phase 0 — protocol spike (now)

- [x] Product thesis and explicit non-goals.
- [x] Minimal Python observation/action/environment contract.
- [x] Deterministic simultaneous-action reference environment.
- [x] Random and heuristic baselines.
- [x] Append-only JSONL trace and basic tests.
- [ ] Resolve RFC 0001 lifecycle, error, and budget semantics.

Exit gate: the same seed and agent versions reproduce environment events, normalized actions, and final payoff.

## Phase 1 — reproducible local tournament

- Tournament manifest, paired seeds, seat swapping, round robin.
- Offline replay verifier and metric recomputation.
- SQLite/Parquet result projection from immutable JSONL traces.
- Confidence intervals, Bradley–Terry rating, cost/quality frontier.
- OpenAI-compatible model adapter with token, latency, and cost telemetry.
- Second environment with different payoff/observability characteristics.

Exit gate: 100+ unattended matches; zero unverifiable completed traces; stable baseline ordering with reported uncertainty.

## Phase 2 — safe external agents

- Language-neutral HTTP adapter and conformance kit.
- Container runner with CPU, memory, time, filesystem, and network policies.
- Signed artifact/config digests and run manifests.
- Prompt-injection and hidden-state leakage test suite.
- Local replay web viewer generated only from scored traces.

Exit gate: a third party can submit an agent without importing platform code, and a hostile sample cannot escape declared capabilities.

## Phase 3 — public research preview

- Seasonal scenario packs and sealed evaluation split.
- Submission API, queue, provenance, rerun policy.
- Public multidimensional leaderboard and curated replays.
- Ancient-strategy flagship environment with 2–4 agents, alliances, communication, partial information, and rule variants.
- Governance process for new environments and metric changes.

Exit gate: at least three independent agent stacks and two environment families produce useful, non-trivial ranking differences.

## First issues to open

1. Finalize `arena.match/v1` and `arena.trace/v1` schemas.
2. Specify budget exhaustion and fallback semantics.
3. Add paired-seed, seat-swapped tournament runner.
4. Build replay verifier from trace plus environment version.
5. Define adapter conformance tests and reference HTTP server.
6. Add telemetry hooks for tokens, tool calls, and monetary cost.
