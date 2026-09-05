"""Configuration and orchestration for fair base-model battles."""

from __future__ import annotations

import os
import tomllib
from collections.abc import Callable, Mapping
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from .agents import OpenAICompatibleAgent
from .core import AgentBudget, ArenaAgent
from .environments import FrontierEnvironment
from .reporting import write_leaderboard_html
from .tournament import TournamentRunner, TournamentSummary

PROVIDERS: Mapping[str, Mapping[str, object]] = {
    "groq": {
        "base_url": "https://api.groq.com/openai/v1",
        "api_key_env": "GROQ_API_KEY",
        "json_response_format": True,
    },
    "gemini": {
        "base_url": "https://generativelanguage.googleapis.com/v1beta/openai",
        "api_key_env": "GEMINI_API_KEY",
        "json_response_format": True,
    },
    "openrouter": {
        "base_url": "https://openrouter.ai/api/v1",
        "api_key_env": "OPENROUTER_API_KEY",
        "json_response_format": True,
    },
    "ollama": {
        "base_url": "http://localhost:11434/v1",
        "api_key_env": "",
        "json_response_format": True,
    },
}

BASE_MODEL_PROMPT_V1 = """You are controlling one player in frontier-v0, a turn-based strategy game.
Your goal is to finish with a higher score than the opponent. Score rewards territory most, then
troops, grain, and morale. Each turn you receive the complete permitted observation, including
public player state, your private event hint, remaining budget, and legal_actions.

Choose exactly one item from legal_actions. Think strategically about resources, defense, attack
risk, remaining turns, and the opponent. Return only one JSON object in this exact shape:
{"kind":"<legal action>","payload":{}}
Do not include analysis, Markdown, or any other keys.
"""

TEMPLATES = {"base-model-v1": BASE_MODEL_PROMPT_V1}


@dataclass(frozen=True, slots=True)
class ModelConfig:
    name: str
    provider: str
    model: str
    base_url: str
    api_key_env: str
    temperature: float = 0.0
    timeout_seconds: float = 30.0
    json_response_format: bool = True
    input_cost_per_million: float = 0.0
    output_cost_per_million: float = 0.0


@dataclass(frozen=True, slots=True)
class BattleConfig:
    name: str
    environment_id: str
    max_turns: int
    seeds: tuple[int, ...]
    output_dir: str
    template: str
    models: tuple[ModelConfig, ModelConfig]
    budget: AgentBudget


def load_battle_config(path: str | Path) -> BattleConfig:
    source = Path(path)
    with source.open("rb") as handle:
        data = tomllib.load(handle)
    if data.get("version") != 1:
        raise ValueError("battle config version must be 1")
    environment = _table(data, "environment")
    if environment.get("id", "frontier-v0") != "frontier-v0":
        raise ValueError("base-model battle v1 supports only frontier-v0")
    raw_models = data.get("models")
    if not isinstance(raw_models, list) or len(raw_models) != 2:
        raise ValueError("battle config must contain exactly two [[models]] entries")
    models = tuple(_model_config(item) for item in raw_models)
    names = [model.name for model in models]
    if len(set(names)) != 2:
        raise ValueError("model names must be unique")
    seeds = tuple(data.get("seeds", [1]))
    if not seeds or any(not isinstance(seed, int) for seed in seeds):
        raise ValueError("seeds must be a non-empty integer array")
    template = str(data.get("template", "base-model-v1"))
    if template not in TEMPLATES:
        raise ValueError(f"unknown agent template: {template}")
    budget_data = data.get("budget", {})
    if not isinstance(budget_data, dict):
        raise ValueError("budget must be a TOML table")
    budget = AgentBudget(
        decision_timeout_ms=int(budget_data.get("decision_timeout_ms", 30_000)),
        max_input_tokens=_optional_int(budget_data, "max_input_tokens"),
        max_output_tokens=_optional_int(budget_data, "max_output_tokens"),
        max_model_calls=_optional_int(budget_data, "max_model_calls"),
        max_tool_calls=_optional_int(budget_data, "max_tool_calls"),
        max_cost_usd=_optional_float(budget_data, "max_cost_usd"),
    )
    return BattleConfig(
        name=str(data.get("name", source.stem)),
        environment_id="frontier-v0",
        max_turns=int(environment.get("max_turns", 6)),
        seeds=seeds,
        output_dir=str(data.get("output_dir", f"runs/{source.stem}")),
        template=template,
        models=(models[0], models[1]),
        budget=budget,
    )


def missing_api_keys(config: BattleConfig) -> tuple[str, ...]:
    return tuple(
        sorted(
            {
                model.api_key_env
                for model in config.models
                if model.api_key_env and not os.environ.get(model.api_key_env)
            }
        )
    )


def run_base_model_battle(config: BattleConfig) -> tuple[TournamentSummary, Path]:
    missing = missing_api_keys(config)
    if missing:
        names = ", ".join(missing)
        raise ValueError(f"missing API key environment variable(s): {names}")
    factories: dict[str, Callable[[int], ArenaAgent]] = {}
    for model in config.models:
        factories[model.name] = _agent_factory(model, TEMPLATES[config.template])
    runner = TournamentRunner(
        lambda: FrontierEnvironment(max_turns=config.max_turns),
        factories,
        budgets=config.budget,
    )
    summary = runner.run(seeds=config.seeds, output_dir=config.output_dir)
    report = write_leaderboard_html(summary, Path(config.output_dir) / "leaderboard.html")
    return summary, report


def _agent_factory(model: ModelConfig, prompt: str) -> Callable[[int], ArenaAgent]:
    def create(seed: int) -> ArenaAgent:
        del seed
        return OpenAICompatibleAgent(
            model=model.model,
            base_url=model.base_url,
            api_key_env=model.api_key_env,
            timeout_seconds=model.timeout_seconds,
            temperature=model.temperature,
            input_cost_per_million=model.input_cost_per_million,
            output_cost_per_million=model.output_cost_per_million,
            system_prompt=prompt,
            json_response_format=model.json_response_format,
        )

    return create


def _model_config(raw: Any) -> ModelConfig:
    if not isinstance(raw, dict):
        raise ValueError("each model entry must be a TOML table")
    provider = str(raw.get("provider", "custom"))
    preset = PROVIDERS.get(provider, {})
    name = str(raw.get("name", "")).strip()
    model = str(raw.get("model", "")).strip()
    base_url = str(raw.get("base_url", preset.get("base_url", ""))).strip()
    api_key_env = str(raw.get("api_key_env", preset.get("api_key_env", ""))).strip()
    if not name or not model or not base_url:
        raise ValueError("each model requires name, model, and a provider or base_url")
    return ModelConfig(
        name=name,
        provider=provider,
        model=model,
        base_url=base_url,
        api_key_env=api_key_env,
        temperature=float(raw.get("temperature", 0.0)),
        timeout_seconds=float(raw.get("timeout_seconds", 30.0)),
        json_response_format=bool(
            raw.get("json_response_format", preset.get("json_response_format", True))
        ),
        input_cost_per_million=float(raw.get("input_cost_per_million", 0.0)),
        output_cost_per_million=float(raw.get("output_cost_per_million", 0.0)),
    )


def _table(data: Mapping[str, Any], key: str) -> Mapping[str, Any]:
    value = data.get(key, {})
    if not isinstance(value, dict):
        raise ValueError(f"{key} must be a TOML table")
    return value


def _optional_int(data: Mapping[str, Any], key: str) -> int | None:
    return int(data[key]) if key in data else None


def _optional_float(data: Mapping[str, Any], key: str) -> float | None:
    return float(data[key]) if key in data else None
