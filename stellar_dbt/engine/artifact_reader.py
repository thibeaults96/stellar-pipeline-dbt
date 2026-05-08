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
    description: str = ""
    depends_on: list[str] = field(default_factory=list)
    depends_on_macros: list[str] = field(default_factory=list)
    columns: dict[str, dict] = field(default_factory=dict)
    config: dict = field(default_factory=dict)
    raw_code: str = ""
    compiled_code: str = ""
    # For test nodes only:
    test_metadata: dict = field(default_factory=dict)
    column_name: str = ""
    attached_node: str = ""


@dataclass
class Manifest:
    nodes: dict[str, ManifestNode] = field(default_factory=dict)
    macros: dict[str, dict] = field(default_factory=dict)

    def find_model(self, name: str) -> ManifestNode | None:
        for node in self.nodes.values():
            if node.resource_type == "model" and node.name == name:
                return node
        return None

    def find_snapshot(self, name: str) -> ManifestNode | None:
        for node in self.nodes.values():
            if node.resource_type == "snapshot" and node.name == name:
                return node
        return None

    def find_macro(self, name: str) -> dict | None:
        for uid, macro in self.macros.items():
            if macro.get("name") == name:
                return macro
        return None

    def find_tests_for_column(
        self, model_name: str, column_name: str, test_name: str | None = None,
    ) -> list[ManifestNode]:
        """Return test nodes attached to the given model.column. If test_name
        is provided, only tests matching that test_metadata.name are returned."""
        out: list[ManifestNode] = []
        for node in self.nodes.values():
            if node.resource_type != "test":
                continue
            meta = node.test_metadata or {}
            kwargs = meta.get("kwargs") or {}
            # The column-attached test node either records column_name on the
            # node directly or in its kwargs; the model is in kwargs.model as a
            # rendered ref('...') string. We match by suffix to avoid having to
            # re-render that.
            col = (node.column_name or kwargs.get("column_name") or "").lower()
            if col != column_name.lower():
                continue
            model_ref = (kwargs.get("model") or "").lower()
            attached = (node.attached_node or "").lower()
            if model_name.lower() not in model_ref and not attached.endswith(f".{model_name.lower()}"):
                continue
            if test_name and meta.get("name") != test_name:
                continue
            out.append(node)
        return out


def read_manifest() -> Manifest | None:
    path = TARGET_DIR / "manifest.json"
    if not path.exists():
        return None

    data = json.loads(path.read_text())
    manifest = Manifest()

    for uid, node in data.get("nodes", {}).items():
        deps_dict = node.get("depends_on") or {}
        manifest.nodes[uid] = ManifestNode(
            unique_id=uid,
            name=node.get("name", ""),
            resource_type=node.get("resource_type", ""),
            description=node.get("description", "") or "",
            depends_on=deps_dict.get("nodes", []) or [],
            depends_on_macros=deps_dict.get("macros", []) or [],
            columns=node.get("columns", {}) or {},
            config=node.get("config", {}) or {},
            raw_code=node.get("raw_code", "") or "",
            compiled_code=node.get("compiled_code", "") or "",
            test_metadata=node.get("test_metadata", {}) or {},
            column_name=node.get("column_name", "") or "",
            attached_node=node.get("attached_node", "") or "",
        )

    # Sources (they appear in manifest.sources, not manifest.nodes)
    for uid, src in data.get("sources", {}).items():
        manifest.nodes[uid] = ManifestNode(
            unique_id=uid,
            name=src.get("name", ""),
            resource_type="source",
            description=src.get("description", "") or "",
            columns=src.get("columns", {}) or {},
            config=src.get("config", {}) or {},
        )

    manifest.macros = data.get("macros", {}) or {}
    return manifest


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
