"""Parses dbt artifacts (manifest.json, run_results.json) for objective checking."""
from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path

from stellar_dbt.config import DBT_PROJECT_DIR

TARGET_DIR = DBT_PROJECT_DIR / "target"


@dataclass
class NodeRunResult:
    unique_id: str
    status: str  # "success", "error", "skipped", "pass", "fail"
    message: str
    execution_time: float
    node_type: str  # "model", "test", "seed", "source"


@dataclass
class RunResults:
    results: list[NodeRunResult] = field(default_factory=list)
    models: list[NodeRunResult] = field(default_factory=list)
    tests: list[NodeRunResult] = field(default_factory=list)
    all_models_passed: bool = False
    all_tests_passed: bool = False
    has_test_failures: bool = False


def read_run_results() -> RunResults | None:
    path = TARGET_DIR / "run_results.json"
    if not path.exists():
        return None

    data = json.loads(path.read_text())
    results = []
    for r in data.get("results", []):
        unique_id = r.get("unique_id", "")
        # Determine node type from unique_id prefix
        if unique_id.startswith("model."):
            node_type = "model"
        elif unique_id.startswith("test."):
            node_type = "test"
        elif unique_id.startswith("seed."):
            node_type = "seed"
        else:
            node_type = "other"

        results.append(NodeRunResult(
            unique_id=unique_id,
            status=r.get("status", "error"),
            message=r.get("message", ""),
            execution_time=r.get("execution_time", 0.0),
            node_type=node_type,
        ))

    models = [r for r in results if r.node_type == "model"]
    tests = [r for r in results if r.node_type == "test"]

    return RunResults(
        results=results,
        models=models,
        tests=tests,
        all_models_passed=len(models) > 0 and all(r.status == "success" for r in models),
        all_tests_passed=len(tests) > 0 and all(r.status == "pass" for r in tests),
        has_test_failures=any(r.status in ("fail", "error") for r in tests),
    )


@dataclass
class ManifestNode:
    unique_id: str
    name: str
    resource_type: str
    depends_on: list[str] = field(default_factory=list)
    columns: dict[str, dict] = field(default_factory=dict)


def read_manifest() -> dict[str, ManifestNode] | None:
    path = TARGET_DIR / "manifest.json"
    if not path.exists():
        return None

    data = json.loads(path.read_text())
    nodes: dict[str, ManifestNode] = {}

    # Models, seeds, snapshots etc.
    for uid, node in data.get("nodes", {}).items():
        deps = node.get("depends_on", {}).get("nodes", [])
        cols = node.get("columns", {})
        nodes[uid] = ManifestNode(
            unique_id=uid,
            name=node.get("name", ""),
            resource_type=node.get("resource_type", ""),
            depends_on=deps,
            columns=cols,
        )

    # Sources (they appear in manifest.sources, not manifest.nodes)
    for uid, src in data.get("sources", {}).items():
        nodes[uid] = ManifestNode(
            unique_id=uid,
            name=src.get("name", ""),
            resource_type="source",
            depends_on=[],
        )

    return nodes


@dataclass
class FreshnessResult:
    unique_id: str  # "source.<project>.<source>.<table>"
    source_name: str
    table_name: str
    status: str  # "pass", "warn", "error", "runtime error"
    max_loaded_at: str | None
    message: str = ""


def read_sources_freshness() -> list[FreshnessResult] | None:
    """Parse target/sources.json from a `dbt source freshness` run."""
    path = TARGET_DIR / "sources.json"
    if not path.exists():
        return None

    data = json.loads(path.read_text())
    out: list[FreshnessResult] = []
    for r in data.get("results", []):
        unique_id = r.get("unique_id", "")
        # unique_id shape: "source.<project>.<source_name>.<table_name>"
        parts = unique_id.split(".")
        source_name = parts[2] if len(parts) >= 4 else ""
        table_name = parts[3] if len(parts) >= 4 else ""
        out.append(FreshnessResult(
            unique_id=unique_id,
            source_name=source_name,
            table_name=table_name,
            status=r.get("status", "runtime error"),
            max_loaded_at=r.get("max_loaded_at"),
            message=r.get("message", "") or "",
        ))
    return out


def get_model_result(model_name: str) -> NodeRunResult | None:
    """Get the run result for a specific model by short name."""
    rr = read_run_results()
    if not rr:
        return None
    return next(
        (r for r in rr.models if r.unique_id.endswith(f".{model_name}")),
        None,
    )
