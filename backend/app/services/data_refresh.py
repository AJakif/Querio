from __future__ import annotations

import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path

from app.core.logging import get_logger


logger = get_logger("services.data_refresh")


@dataclass(frozen=True)
class RefreshStep:
    name: str
    command: tuple[str, ...]
    cwd: Path


class DataRefreshCommandError(RuntimeError):
    def __init__(self, step_name: str, command: tuple[str, ...], cause: Exception):
        self.step_name = step_name
        self.command = command
        self.__cause__ = cause
        super().__init__(f"Data refresh step '{step_name}' failed: {' '.join(command)}")


class DataRefreshPipeline:
    def __init__(
        self,
        command_runner=None,
        python_executable: str | None = None,
        dbt_executable: str = "dbt",
        repo_root: Path | None = None,
    ) -> None:
        self._command_runner = command_runner or self._run_command
        self._python_executable = python_executable or sys.executable
        self._dbt_executable = dbt_executable
        self._repo_root = repo_root or Path(__file__).resolve().parents[3]

    def run(self) -> None:
        for step in self._build_steps():
            logger.info(
                "Running data refresh step",
                extra={"step_name": step.name, "cwd": str(step.cwd), "command": list(step.command)},
            )
            try:
                self._command_runner(step.command, step.cwd)
            except Exception as exc:  # pragma: no cover - exercised via tests with fake runner
                logger.exception(
                    "Data refresh step failed",
                    extra={"step_name": step.name, "cwd": str(step.cwd), "command": list(step.command)},
                )
                raise DataRefreshCommandError(step.name, step.command, exc) from exc
            logger.info("Completed data refresh step", extra={"step_name": step.name})

    def _build_steps(self) -> list[RefreshStep]:
        return [
            RefreshStep(
                name="append_synthetic_orders",
                command=(self._python_executable, "scripts/append_synthetic_orders.py"),
                cwd=self._repo_root / "backend",
            ),
            RefreshStep(
                name="dbt_run",
                command=(self._dbt_executable, "run"),
                cwd=self._repo_root / "dbt",
            ),
        ]

    @staticmethod
    def _run_command(command: tuple[str, ...], cwd: Path) -> None:
        logger.debug("Executing subprocess command", extra={"cwd": str(cwd), "command": list(command)})
        subprocess.run(command, cwd=cwd, check=True)
