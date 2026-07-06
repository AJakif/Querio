from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

from app.core.logging import get_logger


logger = get_logger("orchestration.scheduled_data_refresh_dag")


@dataclass(frozen=True)
class BashTaskSpec:
    task_id: str
    bash_command: str
    cwd: str


@dataclass(frozen=True)
class DagSpec:
    dag_id: str
    schedule: str
    catchup: bool
    task_dict: dict[str, BashTaskSpec] = field(default_factory=dict)


def _repo_root() -> Path:
    root = Path(__file__).resolve().parents[3]
    logger.debug("Resolved repository root", extra={"repo_root": str(root)})
    return root


def _backend_dir() -> Path:
    backend_dir = _repo_root() / "backend"
    logger.debug("Resolved backend directory", extra={"backend_dir": str(backend_dir)})
    return backend_dir


dag = DagSpec(
    dag_id="scheduled_data_refresh",
    schedule="0 * * * *",
    catchup=False,
    task_dict={
        "run_refresh_pipeline": BashTaskSpec(
            task_id="run_refresh_pipeline",
            bash_command="python scripts/run_refresh.py",
            cwd=_backend_dir().as_posix(),
        )
    },
)
