"""Tests for scripts/setup.sh's Ollama auto-detect (Epic 8, Slice 17).

Shells out to the real bash script rather than reimplementing its logic in
Python, since the script itself (not a Python port of it) is what a fresh
clone actually runs. Skips if bash isn't on PATH (e.g. some CI images).
"""

import http.server
import shutil
import subprocess
import threading
from collections.abc import Iterator
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[3]
SETUP_SCRIPT = REPO_ROOT / "scripts" / "setup.sh"


def _find_posix_bash() -> str | None:
    """Locate a real POSIX bash. On Windows, plain "bash" on PATH may
    resolve to the WSL launcher stub instead of a usable shell, so prefer
    Git for Windows' bash if present."""
    for candidate in (
        r"C:\Program Files\Git\bin\bash.exe",
        r"C:\Program Files\Git\usr\bin\bash.exe",
    ):
        if Path(candidate).exists():
            return candidate
    return shutil.which("bash")


BASH = _find_posix_bash()

pytestmark = pytest.mark.skipif(BASH is None, reason="no usable bash found")


class _OkHandler(http.server.BaseHTTPRequestHandler):
    def do_GET(self) -> None:  # noqa: N802 - required by BaseHTTPRequestHandler
        self.send_response(200)
        self.end_headers()
        self.wfile.write(b"{}")

    def log_message(self, *args: object) -> None:  # silence test output
        pass


def _run_setup(
    output_dir: Path,
    probe_url: str,
    extra_args: list[str] | None = None,
) -> subprocess.CompletedProcess[str]:
    assert BASH is not None
    return subprocess.run(
        [BASH, str(SETUP_SCRIPT), *(extra_args or [])],
        cwd=REPO_ROOT,
        env={
            **__import__("os").environ,
            "QUERIO_SETUP_OUTPUT_DIR": str(output_dir),
            "QUERIO_OLLAMA_PROBE_URL": probe_url,
        },
        capture_output=True,
        text=True,
        timeout=30,
        check=True,
    )


# Production defaults for the three context knobs (mirrors .env.example).
_PROD_MAX_RESULT_ROWS = 1000
_PROD_MAX_LLM_ROWS = 50
_PROD_SESSION_BRIEF_MAX_TOKENS = 300


@pytest.fixture
def mock_ollama_server() -> Iterator[str]:
    server = http.server.HTTPServer(("127.0.0.1", 0), _OkHandler)
    port = server.server_address[1]
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        yield f"http://127.0.0.1:{port}"
    finally:
        server.shutdown()
        thread.join(timeout=5)


def test_setup_defaults_to_ollama_when_daemon_detected(
    tmp_path: Path, mock_ollama_server: str
) -> None:
    _run_setup(tmp_path, mock_ollama_server)

    env_contents = (tmp_path / ".env").read_text(encoding="utf-8")
    assert "MODEL_PROVIDER=ollama" in env_contents
    assert f"OLLAMA_BASE_URL={mock_ollama_server}/v1" in env_contents


def test_setup_falls_back_when_ollama_absent(tmp_path: Path) -> None:
    # Port 1 is a privileged port nothing will be listening on; the probe
    # fails fast instead of hanging.
    _run_setup(tmp_path, "http://127.0.0.1:1")

    env_contents = (tmp_path / ".env").read_text(encoding="utf-8")
    assert "MODEL_PROVIDER=openai" in env_contents
    assert (tmp_path / ".env.secrets").exists()


def test_small_model_flag_writes_conservative_values(tmp_path: Path) -> None:
    """--small-model must set all three context knobs to values below production defaults."""
    _run_setup(tmp_path, "http://127.0.0.1:1", extra_args=["--small-model"])

    env_contents = (tmp_path / ".env").read_text(encoding="utf-8")

    def _get_int_value(key: str) -> int:
        for line in env_contents.splitlines():
            if line.startswith(f"{key}="):
                return int(line.split("=", 1)[1])
        raise AssertionError(f"{key} not found in .env")

    assert _get_int_value("MAX_RESULT_ROWS") < _PROD_MAX_RESULT_ROWS
    assert _get_int_value("MAX_LLM_ROWS") < _PROD_MAX_LLM_ROWS
    assert _get_int_value("SESSION_BRIEF_MAX_TOKENS") < _PROD_SESSION_BRIEF_MAX_TOKENS


def test_default_setup_does_not_override_context_knob_defaults(tmp_path: Path) -> None:
    """Without --small-model the three knobs must keep their production defaults."""
    _run_setup(tmp_path, "http://127.0.0.1:1")

    env_contents = (tmp_path / ".env").read_text(encoding="utf-8")
    assert f"MAX_RESULT_ROWS={_PROD_MAX_RESULT_ROWS}" in env_contents
    assert f"MAX_LLM_ROWS={_PROD_MAX_LLM_ROWS}" in env_contents
    assert f"SESSION_BRIEF_MAX_TOKENS={_PROD_SESSION_BRIEF_MAX_TOKENS}" in env_contents
