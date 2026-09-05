# Agent adapters

OpenAgentArena keeps agent policy code outside the environment. An adapter receives one
recipient-specific `Observation` and returns either a plain `Action` or an `AgentDecision`
containing the action, provider-neutral usage, and non-secret provenance metadata.

## In-process Python

Implement one method:

```python
class MyAgent:
    def act(self, observation):
        return Action("harvest")
```

Use this tier only for trusted baselines and environment development. The runner detects a late
return but cannot preempt arbitrary in-process Python code.

## OpenAI-compatible model API

`OpenAICompatibleAgent` targets the common Chat Completions wire shape and asks the model for a
JSON action. It records input/output tokens, model calls, tool calls, estimated cost, model id,
and provider request id.

```python
from open_agent_arena.agents import OpenAICompatibleAgent

agent = OpenAICompatibleAgent(
    model="your-model",
    base_url="https://your-provider.example/v1",
    api_key_env="YOUR_PROVIDER_API_KEY",
    input_cost_per_million=1.0,
    output_cost_per_million=4.0,
)
```

Keys are read at runtime and are never written to a trace. Prices are explicit experiment inputs;
the adapter does not silently fetch mutable pricing tables.

## Language-neutral subprocess

`SubprocessAgent(["python", "agent.py"])` sends one JSON request to stdin and expects one JSON
response on stdout. It enforces a hard subprocess timeout and contains crashes at the runner
boundary.

Request:

```json
{"schema_version":"arena.agent-request/v1","observation":{"agent_id":"red"}}
```

Response:

```json
{
  "action": {"kind": "harvest", "payload": {}},
  "usage": {"input_tokens": 0, "output_tokens": 0, "model_calls": 0,
            "tool_calls": 1, "cost_usd": 0.0},
  "metadata": {"implementation": "example/v1"}
}
```

The subprocess adapter is an execution boundary, **not a security sandbox**. Run untrusted agents
inside a separately configured container or microVM with network, filesystem, CPU, memory, and
process limits.

## Budget behavior

The runner exposes remaining match budgets on each observation. Usage is charged even when a
returned decision exceeds a limit. A timed-out or over-budget decision is replaced by the declared
fallback action, and the trace records the reason. Provider-side adapters should also enforce their
own network timeout so a model request can be cancelled close to the arena deadline.
