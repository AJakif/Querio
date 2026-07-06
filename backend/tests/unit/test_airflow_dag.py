from app.orchestration.scheduled_data_refresh_dag import dag


def test_scheduled_refresh_dag_has_expected_identity():
    assert dag.dag_id == "scheduled_data_refresh"
    assert dag.schedule == "0 * * * *"
    assert dag.catchup is False


def test_scheduled_refresh_dag_contains_refresh_task():
    assert "run_refresh_pipeline" in dag.task_dict

    refresh_task = dag.task_dict["run_refresh_pipeline"]

    assert refresh_task.task_id == "run_refresh_pipeline"
    assert "python scripts/run_refresh.py" in refresh_task.bash_command
    assert refresh_task.cwd.endswith("/backend")
