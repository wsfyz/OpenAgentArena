"""Language-neutral and OpenAI-compatible agent adapters."""

from __future__ import annotations

import json
import os
import subprocess
from collections.abc import Mapping, Sequence
from dataclasses import asdict
from typing import Any
from urllib import request

from ..core import Action, AgentDecision, AgentTimeoutError, AgentUsage, Observation


class SubprocessAgent:
    """Invoke a JSON stdin/stdout agent process once per decision.

    This gives agents a language-neutral process boundary and a hard wall-time
    deadline. It is not a security sandbox; untrusted entries still need a
    container runtime with OS-level filesystem, network, CPU, and memory limits.
    """

    def __init__(
        self,
        command: Sequence[str],
        *,
        timeout_seconds: float = 10.0,
        cwd: str | None = None,
        env: Mapping[str, str] | None = None,
    ) -> None:
        if not command:
            raise ValueError("command cannot be empty")
        if timeout_seconds <= 0:
            raise ValueError("timeout_seconds must be positive")
        self.command = tuple(command)
        self.timeout_seconds = timeout_seconds
        self.cwd = cwd
        self.env = dict(env) if env is not None else None

    def act(self, observation: Observation) -> AgentDecision:
        payload = json.dumps(
            {"schema_version": "arena.agent-request/v1", "observation": asdict(observation)},
            ensure_ascii=False,
        )
        try:
            completed = subprocess.run(
                self.command,
                input=payload,
                text=True,
                capture_output=True,
                timeout=self.timeout_seconds,
                cwd=self.cwd,
                env=self.env,
                check=False,
            )
        except subprocess.TimeoutExpired as exc:
            raise AgentTimeoutError(
                f"subprocess exceeded {self.timeout_seconds:.3f} second deadline"
            ) from exc
        if completed.returncode != 0:
            stderr = completed.stderr.strip()[-500:]
            raise RuntimeError(f"agent exited with {completed.returncode}: {stderr}")
        return _parse_agent_response(completed.stdout)


class OpenAICompatibleAgent:
    """Call any Chat Completions endpoint that implements the OpenAI wire shape."""

    def __init__(
        self,
        *,
        model: str,
        base_url: str,
        api_key: str | None = None,
        api_key_env: str = "OPENAI_API_KEY",
        timeout_seconds: float = 30.0,
        temperature: float = 0.0,
        input_cost_per_million: float = 0.0,
        output_cost_per_million: float = 0.0,
        system_prompt: str | None = None,
        json_response_format: bool = True,
    ) -> None:
        self.model = model
        self.url = base_url.rstrip("/") + "/chat/completions"
        self.api_key = api_key or os.environ.get(api_key_env)
        self.timeout_seconds = timeout_seconds
        self.temperature = temperature
        self.input_cost_per_million = input_cost_per_million
        self.output_cost_per_million = output_cost_per_million
        self.json_response_format = json_response_format
        self.system_prompt = system_prompt or (
            "You are an arena agent. Return only JSON with keys 'kind' and optional "
            "'payload'. The kind must be one of observation.legal_actions."
        )

    def act(self, observation: Observation) -> AgentDecision:
        body: dict[str, Any] = {
            "model": self.model,
            "temperature": self.temperature,
            "messages": [
                {"role": "system", "content": self.system_prompt},
                {
                    "role": "user",
                    "content": json.dumps(asdict(observation), ensure_ascii=False),
                },
            ],
        }
        if self.json_response_format:
            body["response_format"] = {"type": "json_object"}
        headers = {"Content-Type": "application/json"}
        if self.api_key:
            headers["Authorization"] = f"Bearer {self.api_key}"
        req = request.Request(
            self.url,
            data=json.dumps(body).encode(),
            headers=headers,
            method="POST",
        )
        try:
            with request.urlopen(req, timeout=self.timeout_seconds) as response:
                result = json.loads(response.read())
        except TimeoutError as exc:
            raise AgentTimeoutError(
                f"model request exceeded {self.timeout_seconds:.3f} second deadline"
            ) from exc
        try:
            message = result["choices"][0]["message"]
            action_data = _parse_json_content(message["content"])
        except (KeyError, IndexError, TypeError, json.JSONDecodeError) as exc:
            raise ValueError("model response did not contain a JSON action") from exc
        usage_data = result.get("usage", {})
        input_tokens = int(usage_data.get("prompt_tokens", 0))
        output_tokens = int(usage_data.get("completion_tokens", 0))
        cost = (
            input_tokens * self.input_cost_per_million
            + output_tokens * self.output_cost_per_million
        ) / 1_000_000
        return AgentDecision(
            action=Action(action_data["kind"], action_data.get("payload", {})),
            usage=AgentUsage(
                input_tokens=input_tokens,
                output_tokens=output_tokens,
                model_calls=1,
                tool_calls=len(message.get("tool_calls", [])),
                cost_usd=cost,
            ),
            metadata={
                "model": result.get("model", self.model),
                "provider_request_id": result.get("id"),
            },
        )


def _parse_json_content(content: str) -> dict[str, Any]:
    """Accept strict JSON plus the common fenced-JSON model response."""
    cleaned = content.strip()
    if cleaned.startswith("```") and cleaned.endswith("```"):
        cleaned = cleaned[3:-3].strip()
        if cleaned.lower().startswith("json"):
            cleaned = cleaned[4:].lstrip()
    value = json.loads(cleaned)
    if not isinstance(value, dict):
        raise TypeError("model action must be a JSON object")
    return value


def _parse_agent_response(raw: str) -> AgentDecision:
    try:
        data: dict[str, Any] = json.loads(raw)
        action_data = data.get("action", data)
        usage_data = data.get("usage", {})
        return AgentDecision(
            action=Action(action_data["kind"], action_data.get("payload", {})),
            usage=AgentUsage(
                input_tokens=int(usage_data.get("input_tokens", 0)),
                output_tokens=int(usage_data.get("output_tokens", 0)),
                model_calls=int(usage_data.get("model_calls", 0)),
                tool_calls=int(usage_data.get("tool_calls", 0)),
                cost_usd=float(usage_data.get("cost_usd", 0.0)),
            ),
            metadata=data.get("metadata", {}),
        )
    except (KeyError, TypeError, ValueError, json.JSONDecodeError) as exc:
        raise ValueError("agent stdout is not a valid arena response") from exc
