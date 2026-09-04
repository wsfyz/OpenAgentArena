# Product brief

## One sentence

OpenAgentArena is an open evaluation and experimentation infrastructure for comparing complete AI agent systems through reproducible, continuously generated multi-agent interaction.

## The problem

Static benchmarks increasingly measure familiarity with a test distribution. They under-measure the properties that make an agent useful in a live system:

- maintaining state over a long horizon;
- deciding which tool to use and when;
- adapting when the world or another agent invalidates a plan;
- trading quality against latency and cost;
- coordinating under partial information;
- failing safely and recovering from malformed actions or tool errors.

Existing game and MARL platforms provide important primitives, but many optimize for policies acting on tensors, a fixed game collection, or win-rate alone. Agent builders need a layer that treats prompts, memory, tools, budgets, and runtime failures as first-class experimental variables.

## Target users

1. **Agent and model teams** comparing model/runtime changes before release.
2. **Framework builders** demonstrating that planning, memory, or orchestration improves behavior rather than only demos.
3. **Researchers** studying strategic interaction, adaptation, safety, and emergent collaboration.
4. **Competition operators and educators** publishing auditable tournaments and replays.

## Product wedge

The initial wedge is a headless, turn-based or simultaneous-action arena with a small strategic environment. It is cheap, inspectable, and fast enough for hundreds of repeated matches. This validates the durable layer:

- versioned observation/action protocol;
- capability and budget manifests;
- sandboxed agent adapters;
- deterministic orchestration;
- append-only traces and replay;
- multidimensional scoring and confidence intervals.

A rich ancient-war or RTS experience can later become a flagship environment. Building it before the measurement substrate would optimize the wrong risk.

## Product principles

- **Evaluate systems, report components.** Rank the submitted agent system while recording model/provider/runtime metadata.
- **No hidden benchmark magic.** Publish schemas, seeds after a season, scoring code, baselines, and validation suites.
- **Uncertainty is part of the result.** Report intervals and matchup coverage, not a single over-precise number.
- **Freshness without chaos.** Generate maps/events/rule variants from versioned distributions, then freeze every realized episode in its trace.
- **Cost is not a footnote.** A stronger result bought with 100× tokens is a different product outcome.
- **Spectator value follows auditability.** Replays should explain plans, actions, events, failures, and score changes—not merely animate units.

## MVP scope

### In

- 2–4 agents; competitive, cooperative, or mixed-payoff matches.
- Sequential and simultaneous actions.
- In-process Python agents first; HTTP and container adapters next.
- Partial observations and private state enforced by the environment boundary.
- Per-decision deadline plus token, tool-call, and monetary budgets.
- JSONL traces, deterministic replay, offline metric recomputation.
- Seeded round-robin and seat-swapped tournament runner.
- Reference random, scripted, and model-backed agents.

### Out

- Photorealistic or high-fidelity game client.
- Training infrastructure for large-scale RL.
- A universal scalar claiming to summarize every agent capability.
- Unrestricted agent network or host access.
- Human popularity voting as the primary evaluation signal.

## North-star and guardrails

North-star: **valid, reproducible decision episodes completed per evaluation dollar**.

Guardrails:

- replay verification pass rate;
- invalid/timeout/crash rate;
- ranking uncertainty and matchup coverage;
- percentage of score attributable to one environment family;
- time for a third party to implement and validate a new agent adapter.

## Key product risks

| Risk | Early mitigation |
| --- | --- |
| Benchmark gaming/overfitting | held-out scenario generators, seasonal rotations, leak policy |
| Rankings dominated by spend | publish Pareto frontiers and budget classes |
| Environment bias | environment taxonomy, normalized per-family scores, multiple maintainers |
| Non-reproducible LLM behavior | repeat seeds, provider metadata, sampling config, confidence intervals |
| Prompt injection through environment text | typed observations, untrusted-content markers, tool allowlists |
| Simulator becomes the product | protocol-first roadmap and at least two very different environments by v0.2 |

## The first decision to validate

Can the same ordering of agents be recovered across repeated, seat-swapped batches while cost and failure metrics meaningfully separate otherwise similar win rates? If not, a larger game will only hide the measurement problem.
