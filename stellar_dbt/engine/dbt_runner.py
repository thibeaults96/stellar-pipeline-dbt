"""Wraps subprocess calls to dbt CLI commands."""
from __future__ import annotations

import shutil
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path

from stellar_dbt.config import DBT_PROJECT_DIR


def _find_dbt() -> str:
    """Find the dbt executable — prefer the one in the same venv as this package."""
    venv_dbt = Path(sys.executable).parent / "dbt"
    if venv_dbt.exists():
        return str(venv_dbt)
    system_dbt = shutil.which("dbt")
    if system_dbt:
        return system_dbt
    raise RuntimeError("dbt not found. Install it with: pip install dbt-duckdb")


@dataclass
class DbtResult:
    success: bool
    stdout: str
    stderr: str
    return_code: int


def _run_dbt(*args: str, project_dir: Path = DBT_PROJECT_DIR) -> DbtResult:
    cmd = [
        _find_dbt(), *args,
        "--project-dir", str(project_dir.resolve()),
        "--profiles-dir", str(project_dir.resolve()),
    ]
    result = subprocess.run(
        cmd, capture_output=True, text=True, cwd=str(project_dir.resolve()),
    )
    return DbtResult(
        success=result.returncode == 0,
        stdout=result.stdout,
        stderr=result.stderr,
        return_code=result.returncode,
    )


def run() -> DbtResult:
    """Seed then run models — two steps in sequence to ensure seed data exists."""
    seed_result = _run_dbt("seed")
    if not seed_result.success:
        return seed_result
    return _run_dbt("run")


def test() -> DbtResult:
    """Seed then run tests — two steps in sequence to ensure seed data exists."""
    seed_result = _run_dbt("seed")
    if not seed_result.success:
        return seed_result
    return _run_dbt("test")


def seed() -> DbtResult:
    return _run_dbt("seed")


def compile_project() -> DbtResult:
    return _run_dbt("compile")


def build() -> DbtResult:
    """Seed then build (run + test in dependency order)."""
    seed_result = _run_dbt("seed")
    if not seed_result.success:
        return seed_result
    return _run_dbt("build")


def snapshot() -> DbtResult:
    """Seed then run snapshots."""
    seed_result = _run_dbt("seed")
    if not seed_result.success:
        return seed_result
    return _run_dbt("snapshot")


def source_freshness() -> DbtResult:
    """Seed then run source freshness — needs the source table to exist."""
    seed_result = _run_dbt("seed")
    if not seed_result.success:
        return seed_result
    return _run_dbt("source", "freshness")
