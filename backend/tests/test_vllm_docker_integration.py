import json
import os
import shutil
import subprocess
import time
from pathlib import Path
from urllib import error, request

import pytest


PROJECT_ROOT = Path(__file__).resolve().parents[2]
VLLM_SCRIPTS_DIR = PROJECT_ROOT / "scripts" / "vllm"
DEFAULT_ENV_FILE = VLLM_SCRIPTS_DIR / ".env.docker.local"
DEFAULT_COMPOSE_FILE = VLLM_SCRIPTS_DIR / "docker-compose.yml"


def _http_json(
    method: str,
    url: str,
    *,
    payload: dict[str, object] | None = None,
    headers: dict[str, str] | None = None,
) -> dict[str, object]:
    body = None
    req_headers = {"Content-Type": "application/json"}
    if headers:
        req_headers.update(headers)
    if payload is not None:
        body = json.dumps(payload).encode("utf-8")
    req = request.Request(url=url, method=method, data=body, headers=req_headers)
    with request.urlopen(req, timeout=15) as response:
        return json.loads(response.read().decode("utf-8"))


def _wait_for_ready(url: str, timeout_seconds: int = 900) -> None:
    deadline = time.time() + timeout_seconds
    last_error = ""
    while time.time() < deadline:
        try:
            _http_json("GET", url)
            return
        except (error.URLError, error.HTTPError, TimeoutError, json.JSONDecodeError) as exc:
            last_error = str(exc)
            time.sleep(3)
    raise AssertionError(f"Service did not become ready in time: {url}. Last error: {last_error}")


@pytest.mark.integration
def test_vllm_docker_compose_inference() -> None:
    if os.getenv("RUN_DOCKER_INTEGRATION") != "1":
        pytest.skip("Set RUN_DOCKER_INTEGRATION=1 to run Docker integration test.")

    if not shutil.which("docker"):
        pytest.skip("Docker is not installed or not available in PATH.")

    env_file = Path(os.getenv("VLLM_DOCKER_ENV_FILE", str(DEFAULT_ENV_FILE)))
    compose_file = Path(os.getenv("VLLM_DOCKER_COMPOSE_FILE", str(DEFAULT_COMPOSE_FILE)))

    if not env_file.exists():
        pytest.skip(f"Env file not found: {env_file}")
    if not compose_file.exists():
        pytest.skip(f"Compose file not found: {compose_file}")

    env_map: dict[str, str] = {}
    for line in env_file.read_text(encoding="utf-8").splitlines():
        stripped = line.strip()
        if not stripped or stripped.startswith("#") or "=" not in stripped:
            continue
        key, value = stripped.split("=", 1)
        env_map[key] = value

    required = ("VLLM_API_KEY", "PROXY_API_KEY", "PROXY_PORT")
    missing = [key for key in required if not env_map.get(key)]
    if missing:
        pytest.skip(f"Missing required keys in {env_file}: {', '.join(missing)}")

    proxy_port = env_map["PROXY_PORT"]
    proxy_api_key = env_map["PROXY_API_KEY"]
    proxy_base = f"http://127.0.0.1:{proxy_port}"

    compose_cmd = [
        "docker",
        "compose",
        "--env-file",
        str(env_file),
        "-f",
        str(compose_file),
    ]

    started = False
    try:
        subprocess.run(compose_cmd + ["up", "-d", "--build"], check=True, cwd=PROJECT_ROOT)
        started = True
        _wait_for_ready(f"{proxy_base}/health")

        response = _http_json(
            "POST",
            f"{proxy_base}/chat",
            payload={
                "session_id": "itest-vllm-1",
                "message": "Reply exactly with: integration ok",
                "temperature": 0,
                "max_tokens": 32,
            },
            headers={"Authorization": f"Bearer {proxy_api_key}"},
        )

        text = str(response.get("response", "")).lower()
        assert "integration ok" in text
        assert response.get("session_id") == "itest-vllm-1"
    finally:
        if started:
            subprocess.run(compose_cmd + ["down"], check=False, cwd=PROJECT_ROOT)
