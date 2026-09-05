# Base-model battles

[简体中文](base-model-battles.zh-CN.md)

This mode is for users who have API keys but have not built an agent. OpenAgentArena supplies the
same controlled agent shell to both models: one versioned system prompt, the same observation and
action schema, no external tools, the same budgets, identical seeds, and a seat-swapped return
game. The experiment therefore measures model decision quality under this shell. It does **not**
claim to measure the best agent system that could be built around each model.

## Fastest free test: Groq

As of September 2026, Groq documents a Free Plan and lists both `openai/gpt-oss-20b` and
`qwen/qwen3.8-27b` at 30 requests/minute and 1,000 requests/day. Limits and model availability can
change; check the [official rate-limit table](https://console.groq.com/docs/rate-limits) before a
large run.

1. Create a key in the [Groq Console](https://console.groq.com/keys).
2. Keep it outside the repository:

   ```bash
   export GROQ_API_KEY="your-key"
   ```

3. Check the configuration without making model calls, then run it:

   ```bash
   oaa battle examples/battle-groq-free.toml --check
   oaa battle examples/battle-groq-free.toml
   ```

The example runs one seed in both seat orientations: two games, six turns each, and at most 24 API
requests in total. Results appear in `runs/groq-free-smoke-test/` as JSONL traces, a tournament JSON
file, and `leaderboard.html`.

## Other free presets

| Provider | Environment variable | Notes |
| --- | --- | --- |
| Google Gemini | `GEMINI_API_KEY` | The Developer API has a free tier and an [official OpenAI-compatible endpoint](https://ai.google.dev/gemini-api/docs/openai). Free-tier content may be used to improve Google products; review the [official pricing/privacy table](https://ai.google.dev/gemini-api/docs/pricing). |
| OpenRouter | `OPENROUTER_API_KEY` | `openrouter/free` automatically chooses a free model. It is useful for a pipeline smoke test, but changing routing makes it unsuitable for a controlled base-model comparison. See the [official FAQ](https://openrouter.ai/docs/faq). |
| Ollama | none | A local OpenAI-compatible endpoint. It costs no API credits but requires enough local compute and a separately downloaded model. |

Use the corresponding file under `examples/`. Provider model catalogs are not stable, so update the
`model` values if an endpoint reports that a model has been retired.

## What the platform sends

For each turn, the provider receives:

- the versioned `base-model-v1` system prompt;
- the current permitted observation (turn, public state, private hint, legal actions, and budget);
- a request for one JSON action such as `{"kind":"attack","payload":{}}`.

The model is called through Chat Completions. It does not need ChatGPT, an assistant/thread API,
function calling, browser access, or custom code. The arena parses and validates the JSON action,
advances the authoritative environment, and records token usage, latency, errors, scores, and the
provider's returned model/request identifiers.

API keys are read only from environment variables. They are never written to configs or traces.

## Interpreting the result

A one-seed run is a product smoke test, not a benchmark. For a useful comparison, pin exact model
IDs, use several seeds, keep the template and budgets unchanged, repeat runs to expose provider
variance, and compare win rate together with tokens, latency, invalid actions, and failures. The
next protocol revision should add a declared sampling seed where providers support it.
