from __future__ import annotations

import json
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

from open_agent_arena.battle import load_battle_config, run_base_model_battle


class ModelHandler(BaseHTTPRequestHandler):
    requests: list[dict] = []

    def do_POST(self) -> None:  # noqa: N802
        length = int(self.headers["Content-Length"])
        body = json.loads(self.rfile.read(length))
        self.requests.append(body)
        observation = json.loads(body["messages"][1]["content"])
        legal = observation["legal_actions"]
        if body["model"] == "aggressive" and "attack" in legal:
            kind = "attack"
        else:
            kind = "harvest"
        response = json.dumps(
            {
                "id": f"mock-{len(self.requests)}",
                "model": body["model"],
                "choices": [{"message": {"content": json.dumps({"kind": kind})}}],
                "usage": {"prompt_tokens": 50, "completion_tokens": 5},
            }
        ).encode()
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(response)))
        self.end_headers()
        self.wfile.write(response)

    def log_message(self, format: str, *args: object) -> None:
        return


def test_two_models_complete_a_seat_swapped_battle(tmp_path: Path) -> None:
    ModelHandler.requests = []
    server = ThreadingHTTPServer(("127.0.0.1", 0), ModelHandler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    config_path = tmp_path / "battle.toml"
    output_dir = tmp_path / "results"
    config_path.write_text(
        f'''version = 1
name = "mock-model-battle"
seeds = [9]
output_dir = "{output_dir}"

[environment]
max_turns = 3

[budget]
max_model_calls = 3

[[models]]
name = "patient-model"
provider = "custom"
model = "patient"
base_url = "http://127.0.0.1:{server.server_port}/v1"
api_key_env = ""

[[models]]
name = "aggressive-model"
provider = "custom"
model = "aggressive"
base_url = "http://127.0.0.1:{server.server_port}/v1"
api_key_env = ""
''',
        encoding="utf-8",
    )
    try:
        config = load_battle_config(config_path)
        summary, report = run_base_model_battle(config)
    finally:
        server.shutdown()
        thread.join()
        server.server_close()

    assert len(summary.matches) == 2
    assert {standing["played"] for standing in summary.standings} == {2}
    assert len(ModelHandler.requests) == 12
    assert all(
        request["response_format"] == {"type": "json_object"}
        for request in ModelHandler.requests
    )
    assert report.exists()
    assert (output_dir / "tournament.json").exists()
    assert len(list((output_dir / "traces").glob("*.jsonl"))) == 2


def test_free_provider_preset_and_missing_key(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.delenv("GROQ_API_KEY", raising=False)
    path = tmp_path / "groq.toml"
    path.write_text(
        '''version = 1
[[models]]
name = "a"
provider = "groq"
model = "openai/gpt-oss-20b"
[[models]]
name = "b"
provider = "groq"
model = "qwen/qwen3.6-27b"
''',
        encoding="utf-8",
    )
    config = load_battle_config(path)
    assert config.models[0].base_url == "https://api.groq.com/openai/v1"
    assert config.models[0].api_key_env == "GROQ_API_KEY"
