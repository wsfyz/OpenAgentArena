# OpenAgentArena

**An open, dynamic adversarial testbed for AI agents.**

OpenAgentArena evaluates agents by letting them act in shared, evolving environments—not by asking them to solve a fixed list of questions. Under the same rules, tool permissions, information boundaries, and budgets, agents must manage resources, plan over long horizons, adapt to events, and cooperate or compete with other agents.

> Status: **pre-alpha / protocol-first prototype**. The included `frontier` environment is a deliberately small ancient-strategy scenario used to validate the arena contract, deterministic replay, and metrics pipeline. It is not the product boundary.

[简体中文](README.zh-CN.md) · [Base-model battles](docs/base-model-battles.md) · [Product brief](docs/product-brief.md) · [Architecture](docs/architecture.md) · [Evaluation](docs/evaluation.md) · [Agent adapters](docs/agent-adapters.md) · [Landscape](docs/landscape.md) · [Roadmap](docs/roadmap.md)

## Why this exists

Most benchmarks are vertical: every model answers the same fixed task set. OpenAgentArena is horizontal: fresh states emerge from continuous interaction with the world and with other agents. The unit under test is the **agent system**—model, prompts, memory, planning, tools, and runtime—not the base model alone.

The arena is designed around five invariants:

1. **Agent/environment separation** — agents receive observations and return typed actions; they never access hidden state.
2. **Declared capability boundaries** — tools, time, tokens, calls, and monetary budgets are explicit match inputs.
3. **Determinism where possible** — seeds, environment versions, configs, and artifacts make runs reproducible.
4. **Event-sourced evaluation** — every observation, action, error, event, latency, and score is recorded.
5. **Environment independence** — ancient warfare is the first probe, not a hard-coded platform identity.

## What gets measured

| Dimension | Example signals |
| --- | --- |
| Result | win/payoff, objective completion, rating |
| Efficiency | steps, wall time, tool calls, tokens per unit of reward |
| Cost | model and tool spend, compute budget consumed |
| Stability | variance across seeds/opponents/seats, timeout and invalid-action rate |
| Adaptation | performance under held-out rules, events, maps, and opponents |
| Collaboration | team success, communication efficiency, role adherence |

A leaderboard is a view over immutable match traces, not the source of truth.

## Architecture at a glance

```text
Agent adapters                 Arena control plane
┌──────────────┐               ┌────────────────────────────┐
│ LLM / SDK    │── Observation ▶ Match runner + budgets     │
│ Human / Bot  │◀── Action ────│ validation + orchestration │
└──────────────┘               └─────────────┬──────────────┘
                                             │
                         ┌───────────────────┼───────────────────┐
                         ▼                   ▼                   ▼
                  Environment plugin   JSONL event log    Metrics/rating
                  rules + hidden state replay/artifacts   reports/leaderboard
```

The local prototype supports trusted in-process Python, OpenAI-compatible model endpoints, and a
language-neutral subprocess adapter. HTTP/WebSocket and restricted container adapters can be added
without changing environment semantics.

## Quick start

Requires Python 3.11+.

```bash
python -m venv .venv
source .venv/bin/activate
python -m pip install -e ".[dev]"

# Compare two API models under the same controlled agent template
export GROQ_API_KEY="your-key"
oaa battle examples/battle-groq-free.toml --check
oaa battle examples/battle-groq-free.toml

# Built-in non-AI demos
oaa run --seed 7 --log runs/demo.jsonl
oaa commons --seed 7 --log runs/commons.jsonl
oaa tournament --seeds 1,2,3,4,5 --output-dir runs/tournament
oaa verify runs/demo.jsonl
oaa replay runs/demo.jsonl --output runs/replay.html
pytest
```

Example output:

```json
{
  "environment": "frontier-v0",
  "winner": "red",
  "turns": 12,
  "scores": {"red": 4.7, "blue": 3.8}
}
```

## Repository map

```text
src/open_agent_arena/
  core.py                  # stable agent/environment data contract
  runner.py                # orchestration, budgets, telemetry, event trace
  tournament.py            # paired seeds, seat swaps, round robin, Elo
  replay.py                # offline deterministic trace verification
  reporting.py             # static leaderboard and replay viewer
  agents/adapters.py       # OpenAI-compatible and subprocess agents
  agents/baselines.py      # random and heuristic reference agents
  environments/frontier.py # first deterministic strategy probe
  environments/commons.py  # three-agent cooperation/competition probe
docs/                      # product, architecture, evaluation, research, roadmap
rfcs/0001-arena-protocol.md
tests/
```

## Implemented evaluation loop

The local prototype now runs paired-seed, seat-swapped round robins; records latency, tokens,
model/tool calls, cost, timeouts, and budget exhaustion; verifies scored traces by re-executing the
environment; and emits dependency-free HTML leaderboard and replay artifacts. The provided Elo is
a convenient live view, not a substitute for the immutable match set.

`frontier-v0` tests two-player adversarial planning with full public state. `commons-v0` tests three
agents under partial observability, private reserves, shared-resource collapse, cooperation, and
free-riding. Together they keep the platform contract independent from a single game shape.

## Near-term milestone

The first meaningful milestone is not a polished RTS. It is a reproducible tournament in which:

- a random bot, heuristic bot, and two model-backed agents use the same versioned API;
- 100+ seeded, seat-swapped matches run without operator intervention;
- every run can be replayed and independently rescored;
- outcome, latency, token/tool usage, cost, and failure rates are shown together;
- an unseen rule variant tests adaptation rather than memorization.

See the [roadmap](docs/roadmap.md) and [protocol RFC](rfcs/0001-arena-protocol.md) to contribute.

## License

Apache-2.0. See [LICENSE](LICENSE).
