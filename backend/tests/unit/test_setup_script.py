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


def _run_setup(output_dir: Path, probe_url: str) -> subprocess.CompletedProcess[str]:
    assert BASH is not None
    return subprocess.run(
        [BASH, str(SETUP_SCRIPT)],
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
