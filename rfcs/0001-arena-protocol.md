# RFC 0001: Agent–environment protocol

- Status: Draft
- Authors: OpenAgentArena contributors
- Target: `arena.protocol/v1`

## Summary

Define the smallest transport-independent contract required to run, audit, and replay dynamic multi-agent evaluations.

## Requirements

- sequential and simultaneous-action environments;
- recipient-specific partial observations;
- structured legal actions and validation errors;
- per-decision and per-match budgets;
- deterministic environment randomness from an owned seed stream;
- lifecycle hooks for initialization, action, terminal state, and shutdown;
- telemetry envelopes that do not alter environment semantics;
- explicit protocol and environment versions.

## Proposed messages

### Initialize

Runner to agent:

```json
{
  "type": "initialize",
  "protocol": "arena.protocol/v1",
  "match_id": "...",
  "agent_id": "red",
  "environment": {"id": "frontier", "version": "v0"},
  "capabilities": {"tools": [], "network": "none"},
  "budgets": {"decision_timeout_ms": 10000, "max_tool_calls": 100}
}
```

### Observe / act

```json
{
  "type": "observation",
  "match_id": "...",
  "step": 4,
  "agent_id": "red",
  "public": {},
  "private": {},
  "legal_actions": [
    {"kind": "attack", "schema": {"type": "object", "properties": {}}}
  ],
  "budget_remaining": {"wall_ms": 10000, "tool_calls": 87}
}
```

```json
{
  "type": "action",
  "match_id": "...",
  "step": 4,
  "kind": "attack",
  "payload": {},
  "client_action_id": "..."
}
```

### Result / shutdown

The runner returns an action receipt describing accepted, normalized, rejected, timed-out, or fallback status. At terminal state it sends the agent-visible outcome before requesting shutdown. Hidden information is disclosed only according to the tournament policy.

## Open questions

1. Are legal actions enumerated instances, JSON Schemas, or tool definitions? Recommendation: schema plus optional bounded examples.
2. Should agent retries consume environment time only, or a separate protocol retry budget? Recommendation: both are recorded; tournament policy decides eligibility.
3. Can agents send messages outside environment actions? Recommendation: no side channel; communication is an environment-defined action.
4. How are streaming actions handled in real-time environments? Defer to a v1 extension after turn-based conformance is stable.
5. Which telemetry is trusted when the agent is remote? Separate runner-measured and agent-reported namespaces.

## Compatibility

The Python prototype now implements the observe/act subset as `arena.agent-request/v1` for the
subprocess adapter. An adapter may return a bare action or an envelope containing action, usage,
and metadata. The runner owns the authoritative stopwatch and cumulative budget counters. Usage is
charged before limit evaluation; late or over-budget decisions become declared fallback actions and
remain visible in `arena.trace/v1` telemetry.

Initialization, receipts, retry semantics, shutdown, and idempotency remain draft. A future
conformance suite must validate serialization, hidden-state isolation, deadline behavior,
idempotency, and trace completeness across transports.
