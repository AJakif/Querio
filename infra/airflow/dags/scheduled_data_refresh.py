from __future__ import annotations

import sys
from datetime import datetime
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[3]
BACKEND_ROOT = REPO_ROOT / "backend"

if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))

from app.orchestration.scheduled_data_refresh_dag import dag as dag_spec

try:
    from airflow import DAG
    from airflow.operators.bash import BashOperator
except ImportError as exc:  # pragma: no cover
    raise RuntimeError(
        "apache-airflow must be installed to load the scheduled data refresh DAG."
    ) from exc


with DAG(
    dag_id=dag_spec.dag_id,
    schedule=dag_spec.schedule,
    catchup=dag_spec.catchup,
    start_date=datetime(2024, 1, 1),
    tags=["querio", "data-refresh"],
) as dag:
    refresh_task = dag_spec.task_dict["run_refresh_pipeline"]

    BashOperator(
        task_id=refresh_task.task_id,
        bash_command=refresh_task.bash_command,
        cwd=refresh_task.cwd,
    )
