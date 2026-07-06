from pathlib import Path

import pytest

from app.services.data_refresh import DataRefreshCommandError, DataRefreshPipeline


class RecordingRunner:
    def __init__(self, failing_command: tuple[str, ...] | None = None):
        self.calls: list[tuple[tuple[str, ...], Path]] = []
        self.failing_command = failing_command

    def __call__(self, command: tuple[str, ...], cwd: Path) -> None:
        self.calls.append((command, cwd))
        if self.failing_command == command:
            raise RuntimeError("boom")


def test_refresh_pipeline_runs_raw_load_then_dbt_run():
    runner = RecordingRunner()
    pipeline = DataRefreshPipeline(
        command_runner=runner,
        python_executable="python-test",
        dbt_executable="dbt-test",
    )

    pipeline.run()

    assert runner.calls == [
        (
            ("python-test", "scripts/append_synthetic_orders.py"),
            Path(__file__).resolve().parents[3] / "backend",
        ),
        (("dbt-test", "run"), Path(__file__).resolve().parents[3] / "dbt"),
        (("dbt-test", "test"), Path(__file__).resolve().parents[3] / "dbt"),
    ]


def test_refresh_pipeline_raises_step_name_when_command_fails():
    runner = RecordingRunner(failing_command=("dbt-test", "run"))
    pipeline = DataRefreshPipeline(
        command_runner=runner,
        python_executable="python-test",
        dbt_executable="dbt-test",
    )

    with pytest.raises(DataRefreshCommandError) as exc_info:
        pipeline.run()

    assert exc_info.value.step_name == "dbt_run"
    assert exc_info.value.command == ("dbt-test", "run")
    assert "dbt_run" in str(exc_info.value)


def test_refresh_pipeline_raises_for_dbt_test_failures():
    runner = RecordingRunner(failing_command=("dbt-test", "test"))
    pipeline = DataRefreshPipeline(
        command_runner=runner,
        python_executable="python-test",
        dbt_executable="dbt-test",
    )

    with pytest.raises(DataRefreshCommandError) as exc_info:
        pipeline.run()

    assert exc_info.value.step_name == "dbt_test"
    assert exc_info.value.command == ("dbt-test", "test")


def test_refresh_pipeline_allows_repo_root_override():
    runner = RecordingRunner()
    pipeline = DataRefreshPipeline(
        command_runner=runner,
        python_executable="python-test",
        dbt_executable="dbt-test",
        repo_root=Path("D:/tmp/querio"),
    )

    pipeline.run()

    assert runner.calls == [
        (("python-test", "scripts/append_synthetic_orders.py"), Path("D:/tmp/querio/backend")),
        (("dbt-test", "run"), Path("D:/tmp/querio/dbt")),
        (("dbt-test", "test"), Path("D:/tmp/querio/dbt")),
    ]
