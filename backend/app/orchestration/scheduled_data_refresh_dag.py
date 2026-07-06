from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path


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
    return Path(__file__).resolve().parents[3]


def _backend_dir() -> Path:
    return _repo_root() / "backend"


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
