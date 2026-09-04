# Contributing

OpenAgentArena is pre-alpha. The most valuable early contributions make experiments more reproducible, interfaces smaller, or measurements harder to game.

## Development

```bash
python -m venv .venv
source .venv/bin/activate
python -m pip install -e ".[dev]"
ruff check .
pytest
```

## Pull requests

- Open an issue or RFC before a breaking protocol, trace, or metric change.
- Add tests for environment determinism and hidden-state boundaries.
- Version behavior-changing environments rather than silently changing old scores.
- Keep model/provider dependencies behind adapters.
- Include a migration note when a trace or manifest schema changes.

By participating, you agree to follow the [Code of Conduct](CODE_OF_CONDUCT.md).
