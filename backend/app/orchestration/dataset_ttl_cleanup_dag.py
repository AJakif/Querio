"""Airflow DAG spec for the dataset TTL cleanup job (T9c).

Runs daily at 02:00 UTC.  Drops session-scoped Postgres schemas whose
datasets have exceeded DATASET_TTL_DAYS (default 30 days) and marks the
corresponding chat sessions as expired so the ask flow can return a
user-friendly re-upload prompt.

Follows the same pattern as scheduled_data_refresh_dag.py — a pure-Python
DagSpec that the Airflow entrypoint mounts and wires into a real DAG.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

from app.core.logging import get_logger


logger = get_logger("orchestration.dataset_ttl_cleanup_dag")


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


def _backend_dir() -> Path:
    backend_dir = Path(__file__).resolve().parents[2]
    logger.debug("Resolved backend directory", extra={"backend_dir": str(backend_dir)})
    return backend_dir


dag = DagSpec(
    dag_id="dataset_ttl_cleanup",
    schedule="0 2 * * *",
    catchup=False,
    task_dict={
        "run_dataset_ttl_cleanup": BashTaskSpec(
            task_id="run_dataset_ttl_cleanup",
            bash_command="python scripts/run_dataset_ttl_cleanup.py",
            cwd=_backend_dir().as_posix(),
        )
    },
)
