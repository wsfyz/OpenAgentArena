# Architecture

## Design goals

- Environment authors implement rules once and can use local, HTTP, or container agents.
- Agent authors depend on a small, versioned contract rather than environment internals.
- Match execution is deterministic except for declared external-model nondeterminism.
- Traces are sufficient to replay environment transitions and recompute metrics.
- Capability boundaries can be enforced and audited.

## Logical components

```text
                           Control plane
┌───────────────┐    ┌────────────────────────┐    ┌──────────────────┐
│ Tournament    │───▶│ Match scheduler        │───▶│ Sandbox/runtime  │
│ specification │    │ seeds, seats, budgets │    │ lifecycle        │
└───────────────┘    └───────────┬────────────┘    └────────┬─────────┘
                                │                           │
                                ▼                           ▼
                       ┌────────────────┐          ┌──────────────────┐
                       │ Environment    │◀────────▶│ Agent adapter    │
                       │ authoritative  │ obs/act  │ model/tools/mem  │
                       │ state machine  │          │                  │
                       └───────┬────────┘          └────────┬─────────┘
                               │                            │
                               └────────────┬───────────────┘
                                            ▼
                                  ┌──────────────────┐
                                  │ Append-only trace│
                                  │ + artifacts      │
                                  └────────┬─────────┘
                                           ▼
                                  ┌──────────────────┐
                                  │ Replay, metrics, │
                                  │ ratings, reports │
                                  └──────────────────┘
```

## Core contract

An environment owns authoritative state and exposes:

- `reset(seed) -> observations_by_agent`
- `step(actions_by_agent) -> StepResult`

An agent exposes:

- `act(observation) -> action`

The observation includes only the recipient's allowed public/private view, legal action kinds, current step, and remaining budgets. An action contains a versioned `kind` and typed payload. The runner owns deadlines, retries, fallback policy, logging, and lifecycle.

The prototype implements this contract in [`src/open_agent_arena/core.py`](../src/open_agent_arena/core.py).
Trusted Python, OpenAI-compatible endpoints, and JSON subprocess agents share the same semantic
contract; see [Agent adapters](agent-adapters.md). RFC 0001 defines the intended wire representation.

## Match specification

Every match should be fully described by a serializable manifest:

```yaml
schema_version: arena.match/v1
environment:
  id: frontier
  version: v0
  config_digest: sha256:...
seed: 7
agents:
  - seat: red
    artifact_digest: sha256:...
    adapter: container/v1
budgets:
  decision_timeout_ms: 10000
  max_model_tokens: 50000
  max_tool_calls: 100
  max_cost_usd: 1.00
network_policy: none
```

Digests prevent a mutable image, prompt, or scenario config from silently changing the meaning of a result.

## Trace model

Use append-only JSONL for the early system because it is streamable, diffable, failure-tolerant, and easy to archive. Each record has:

- schema and environment version;
- match/episode/turn identity;
- recipient-specific observations or their content hashes;
- raw and normalized action;
- validation status and fallback reason;
- environment events, rewards, termination state;
- latency, token/tool/cost telemetry;
- a hash chain field once adversarial submissions are enabled.

Large artifacts (screenshots, model transcripts, maps) should be content-addressed and referenced by digest. Public replays must redact secrets and hidden observations until disclosure is permitted.

## Execution tiers

1. **In-process** — trusted baselines and environment development, with post-return deadline accounting.
2. **Local process** — implemented JSON stdin/stdout adapter with a hard subprocess timeout.
3. **Model endpoint** — implemented OpenAI-compatible adapter with provider-neutral usage telemetry.
4. **Container** — untrusted submissions with CPU, memory, filesystem, network, and time limits.
5. **Remote endpoint** — organization-hosted agents, signed requests, and weaker reproducibility.

## Fairness and security boundary

- Seat swap whenever position can affect payoffs.
- Use paired seeds so compared agents face the same realized randomness.
- Never expose authoritative or other agents' private state through errors, logs, tool results, or timing when avoidable.
- Enforce outbound network and tool allowlists outside the agent process.
- Treat natural-language environment content as untrusted data.
- Sign submitted artifact/config digests and make scoring code independently runnable.

## Evolution strategy

Keep the semantic contract smaller than the transport. Add HTTP/WebSocket, MCP, or gRPC adapters around `Observation`, `Action`, and lifecycle messages; do not let a transport dictate environment rules. Breaking environment changes receive a new environment version. Breaking protocol changes receive a new schema major version.
