"""Check objectives against real dbt artifacts, files, and DuckDB."""
from __future__ import annotations

import re
from dataclasses import dataclass
from difflib import get_close_matches
from pathlib import Path

import duckdb
import yaml

from stellar_dbt.config import DBT_PROJECT_DIR, DB_PATH
from stellar_dbt.models.game_types import ObjectiveCheck, ObjectiveDefinition
from stellar_dbt.engine import artifact_reader


@dataclass
class CheckResult:
    passed: bool
    reason: str | None = None

    def __bool__(self) -> bool:
        return self.passed


def _ok() -> CheckResult:
    return CheckResult(True)

def _fail(reason: str) -> CheckResult:
    return CheckResult(False, reason)


def _read_file(filename: str) -> str:
    path = DBT_PROJECT_DIR / filename
    return path.read_text() if path.exists() else ""


def _strip_comments(sql: str) -> str:
    return re.sub(r"--.*$", "", sql, flags=re.MULTILINE)


def check(objective: ObjectiveDefinition) -> CheckResult:
    return _check(objective.check)


def _check(c: ObjectiveCheck) -> CheckResult:

    # ── File-content checks ──────────────────────────────────────────────

    if c.type == "has_column_alias":
        from stellar_dbt.engine._sql_helpers import extract_column_aliases
        sql = _read_file(c.filename)
        if not sql.strip():
            return _fail(f"File '{c.filename}' is empty.")
        aliases = extract_column_aliases(sql)
        missing = [a for a in c.aliases if a.lower() not in aliases]
        if missing:
            if aliases:
                return _fail(f"Missing column alias(es): {', '.join(missing)}. Found: {', '.join(aliases[:8])}. Use 'column AS alias_name'.")
            return _fail(f"No column aliases found. Use 'column AS {missing[0]}' syntax in your SELECT.")
        return _ok()

    if c.type == "has_ref_call":
        content = _strip_comments(_read_file(c.filename))
        if not content.strip():
            return _fail(f"File '{c.filename}' is empty. Add a SELECT that uses {{{{ ref('{c.target_model}') }}}}.")
        pattern = rf"\{{\{{\s*ref\s*\(\s*['\"]{ re.escape(c.target_model) }['\"]\s*\)\s*\}}\}}"
        if not re.search(pattern, content):
            if "ref(" in content:
                return _fail(f"Found a ref() call, but not one targeting '{c.target_model}'. Use: {{{{ ref('{c.target_model}') }}}}")
            return _fail(f"No ref('{c.target_model}') found. Use: {{{{ ref('{c.target_model}') }}}}")
        return _ok()

    if c.type == "file_contains_active_sql":
        raw = _read_file(c.filename)
        if not raw.strip():
            return _fail(f"File '{c.filename}' is empty.")
        stripped = _strip_comments(raw)
        try:
            if not re.search(c.pattern, stripped, re.IGNORECASE):
                near_miss = _detect_near_miss(c.pattern, stripped)
                basename = c.filename.rsplit("/", 1)[-1]
                if near_miss:
                    return _fail(f"Close, but not quite in {basename}: {near_miss}")
                return _fail(f"Not found in {basename}. Check the objective hint for what's needed.")
            return _ok()
        except re.error:
            return _fail(f"Not found in {c.filename}.")

    if c.type == "file_contains":
        content = _read_file(c.filename)
        if not content.strip():
            return _fail(f"File '{c.filename}' is empty.")
        try:
            if not re.search(c.pattern, content, re.IGNORECASE):
                return _fail(f"Required content not found in {c.filename}.")
            return _ok()
        except re.error:
            return _fail(f"Required content not found in {c.filename}.")

    if c.type == "no_hardcoded_refs":
        content = _read_file(c.filename)
        uncommented = _strip_comments(content)
        if not re.search(r"\{\{\s*(ref|source)\s*\(", uncommented):
            return _fail(f"No ref() or source() calls found. Use {{{{ ref('model_name') }}}} instead of direct table names.")
        stripped = re.sub(r"\{\{[^}]+\}\}", "", uncommented)
        hardcoded = re.search(r"\b(?:from|join)\s+(\w+\.\w+)", stripped, re.IGNORECASE)
        if hardcoded:
            return _fail(f"Found hardcoded table reference '{hardcoded.group(1)}'. Replace with a ref() call.")
        return _ok()

    if c.type == "has_test":
        for path in DBT_PROJECT_DIR.rglob("*.yml"):
            if not path.is_file() or "target" in path.parts:
                continue
            text = path.read_text()
            if c.model_name not in text:
                continue
            pattern = rf"name:\s*{re.escape(c.column_name)}[\s\S]*?tests:[\s\S]*?-\s*{re.escape(c.test_type)}"
            if re.search(pattern, text):
                return _ok()
        return _fail(f"Test '{c.test_type}' not found on column '{c.column_name}' in any YAML schema file for model '{c.model_name}'.")

    if c.type == "has_freshness_config":
        return _check_freshness_config(c.source_name, c.table_name)

    # ── Artifact-based checks ────────────────────────────────────────────

    if c.type == "all_models_pass":
        rr = artifact_reader.read_run_results()
        if not rr or not rr.models:
            return _fail("You haven't run dbt yet. Click 'dbt run' or press Cmd+Enter.")
        if not rr.all_models_passed:
            failed = [r for r in rr.models if r.status != "success"]
            names = [r.unique_id.split(".")[-1] for r in failed[:3]]
            return _fail(f"Not all models passed. Failed: {', '.join(names)}. Check the dbt output for details.")
        return _ok()

    if c.type == "model_passes":
        result = artifact_reader.get_model_result(c.model)
        if not result:
            return _fail(f"No run result for model '{c.model}'. Click 'dbt run' or press Cmd+Enter first.")
        if result.status != "success":
            return _fail(f"Model '{c.model}' had status '{result.status}': {result.message}")
        return _ok()

    if c.type == "source_freshness_ran":
        results = artifact_reader.read_sources_freshness()
        if not results:
            return _fail(
                "No source freshness results yet. Click 'dbt freshness' "
                "in the toolbar to run it."
            )
        target = next(
            (r for r in results if r.source_name == c.source_name and r.table_name == c.table_name),
            None,
        )
        if not target:
            return _fail(
                f"Source `{c.source_name}.{c.table_name}` wasn't included in the last "
                "freshness run. Make sure it's defined and has a freshness config, "
                "then click 'dbt freshness' again."
            )
        if target.status == "runtime error":
            msg = target.message or "see terminal output"
            return _fail(
                f"`dbt source freshness` errored on `{c.source_name}.{c.table_name}` ({msg}). "
                "Fix the config and run it again."
            )
        # pass / warn / error all mean dbt successfully evaluated freshness —
        # the config is structurally valid, which is what we want to confirm.
        return _ok()

    if c.type == "tests_ran_with_failures":
        rr = artifact_reader.read_run_results()
        if not rr:
            return _fail("You haven't run tests yet. Click 'dbt test'.")
        if not rr.tests:
            return _fail("No tests were found. Make sure your YAML file defines tests under column definitions.")
        if not rr.has_test_failures:
            return _fail("All tests passed — but the source data has known issues. Your tests should catch the bad rows.")
        return _ok()

    # ── DuckDB checks ────────────────────────────────────────────────────

    if c.type == "duckdb_column_exists":
        try:
            conn = duckdb.connect(str(DB_PATH), read_only=True)
            result = conn.execute(
                "SELECT column_name FROM information_schema.columns WHERE table_name = ? AND column_name = ?",
                [c.table, c.column],
            ).fetchone()
            conn.close()
            if result:
                return _ok()
            return _fail(f"Column '{c.column}' not found in table '{c.table}'.")
        except Exception as e:
            return _fail(f"Could not query database: {e}")

    if c.type == "duckdb_columns_exist":
        if not DB_PATH.exists():
            return _fail("No database yet. Run 'dbt run' first.")
        try:
            conn = duckdb.connect(str(DB_PATH), read_only=True)
            # Check if table exists
            exists = conn.execute(
                "SELECT 1 FROM information_schema.tables WHERE table_name = ? AND table_schema = 'main'",
                [c.table],
            ).fetchone()
            if not exists:
                conn.close()
                return _fail(f"Model '{c.table}' not found. Run 'dbt run' to build it.")
            # Get actual columns and types
            actual = conn.execute(
                "SELECT column_name, data_type FROM information_schema.columns WHERE table_name = ? AND table_schema = 'main'",
                [c.table],
            ).fetchall()
            conn.close()
            actual_cols = {row[0].lower(): row[1].upper() for row in actual}
            missing = [col for col in c.columns if col.lower() not in actual_cols]
            if missing:
                found = list(actual_cols.keys())
                return _fail(f"Missing column(s) in {c.table}: {', '.join(missing)}. Found: {', '.join(found)}")
            # Check types if specified
            for col, expected_type in c.types.items():
                actual_type = actual_cols.get(col.lower(), "")
                if expected_type.upper() not in actual_type:
                    return _fail(f"Column '{col}' in {c.table} has type {actual_type}, expected {expected_type}.")
            return _ok()
        except Exception as e:
            return _fail(f"Could not query database: {e}")

    if c.type == "duckdb_column_values":
        if not DB_PATH.exists():
            return _fail("No database yet. Run 'dbt run' first.")
        try:
            conn = duckdb.connect(str(DB_PATH), read_only=True)
            violations = conn.execute(c.query).fetchall()
            conn.close()
            if len(violations) > 0:
                return _fail(f"Found {len(violations)} row(s) that don't match in {c.table}. Check the data preview.")
            return _ok()
        except Exception as e:
            return _fail(f"Query failed: {e}")

    if c.type == "duckdb_row_count":
        if not DB_PATH.exists():
            return _fail("No database yet. Run 'dbt run' first.")
        try:
            conn = duckdb.connect(str(DB_PATH), read_only=True)
            if c.where:
                count = conn.execute(f'SELECT count(*) FROM main."{c.table}" WHERE {c.where}').fetchone()[0]
                total = conn.execute(f'SELECT count(*) FROM main."{c.table}"').fetchone()[0]
            else:
                count = conn.execute(f'SELECT count(*) FROM main."{c.table}"').fetchone()[0]
                total = count
            conn.close()
            if count < c.min_rows:
                if c.where:
                    return _fail(f"Expected at least {c.min_rows} row(s) matching condition in {c.table}, got {count} out of {total}.")
                return _fail(f"Expected at least {c.min_rows} row(s) in {c.table}, got {count}.")
            return _ok()
        except Exception as e:
            return _fail(f"Query failed: {e}")

    if c.type == "snapshot_ran":
        if not DB_PATH.exists():
            return _fail("No database yet. Run 'dbt snapshot' first.")
        try:
            conn = duckdb.connect(str(DB_PATH), read_only=True)
            exists = conn.execute(
                "SELECT 1 FROM information_schema.tables WHERE table_name = ? AND table_schema = 'main'",
                [c.table],
            ).fetchone()
            conn.close()
            if exists:
                return _ok()
            return _fail(f"Snapshot table '{c.table}' not found. Click 'dbt snapshot' to run it.")
        except Exception as e:
            return _fail(f"Could not query database: {e}")

    # ── Manifest-based checks ────────────────────────────────────────────

    if c.type == "manifest_model_config":
        manifest = _require_manifest()
        if isinstance(manifest, CheckResult):
            return manifest
        node = manifest.find_model(c.model)
        if not node:
            return _fail(f"Model '{c.model}' not found in dbt manifest. Run dbt to compile it.")
        actual = node.config.get(c.key)
        if actual is None or actual == "":
            return _fail(
                f"Model '{c.model}' has no `{c.key}` configured. "
                f"Add it to the {{{{ config(...) }}}} block."
            )
        if str(actual).strip().lower() != c.value.strip().lower():
            return _fail(
                f"Model '{c.model}' has {c.key}={actual!r}, expected {c.value!r}."
            )
        return _ok()

    if c.type == "manifest_model_description":
        manifest = _require_manifest()
        if isinstance(manifest, CheckResult):
            return manifest
        node = manifest.find_model(c.model)
        if not node:
            return _fail(f"Model '{c.model}' not found in dbt manifest. Run dbt to compile it.")
        desc = (node.description or "").strip()
        if not desc:
            return _fail(f"Model '{c.model}' has no description in its YAML.")
        if len(desc) < c.min_length:
            return _fail(
                f"Description on '{c.model}' is too short ({len(desc)} chars). "
                f"Write at least {c.min_length} characters explaining what this model does."
            )
        return _ok()

    if c.type == "manifest_column_description":
        manifest = _require_manifest()
        if isinstance(manifest, CheckResult):
            return manifest
        node = manifest.find_model(c.model)
        if not node:
            return _fail(f"Model '{c.model}' not found in dbt manifest. Run dbt to compile it.")
        col = next(
            (v for k, v in node.columns.items() if k.lower() == c.column.lower()),
            None,
        )
        if not col:
            return _fail(
                f"Column '{c.column}' not declared in '{c.model}'s YAML. "
                "Add it under columns: with a description."
            )
        desc = ((col.get("description") if isinstance(col, dict) else "") or "").strip()
        if not desc:
            return _fail(f"Column '{c.column}' on '{c.model}' has no description in its YAML.")
        if len(desc) < c.min_length:
            return _fail(
                f"Description on '{c.model}.{c.column}' is too short ({len(desc)} chars). "
                f"Write at least {c.min_length} characters explaining what this column means."
            )
        return _ok()

    if c.type == "manifest_column_test":
        manifest = _require_manifest()
        if isinstance(manifest, CheckResult):
            return manifest
        if not manifest.find_model(c.model):
            return _fail(f"Model '{c.model}' not found in dbt manifest. Run dbt to compile it.")
        tests = manifest.find_tests_for_column(c.model, c.column, c.test_name)
        if not tests:
            return _fail(
                f"No `{c.test_name}` test on `{c.model}.{c.column}` in the manifest. "
                f"Add it under the column's tests: list."
            )
        if c.test_name == "accepted_values":
            for test_node in tests:
                values = (test_node.test_metadata or {}).get("kwargs", {}).get("values") or []
                values_set = {str(v).lower() for v in values}
                missing = [v for v in c.required_values if v.lower() not in values_set]
                forbidden_present = [v for v in c.forbidden_values if v.lower() in values_set]
                if missing:
                    return _fail(
                        f"`accepted_values` on `{c.model}.{c.column}` is missing: "
                        f"{', '.join(repr(v) for v in missing)}. "
                        f"Found values: {sorted(values_set)}."
                    )
                if forbidden_present:
                    return _fail(
                        f"`accepted_values` on `{c.model}.{c.column}` includes "
                        f"value(s) it shouldn't: {', '.join(repr(v) for v in forbidden_present)}. "
                        "Those represent invalid data the test should catch."
                    )
                return _ok()
        return _ok()

    if c.type == "manifest_model_depends_on_macro":
        manifest = _require_manifest()
        if isinstance(manifest, CheckResult):
            return manifest
        node = manifest.find_model(c.model)
        if not node:
            return _fail(f"Model '{c.model}' not found in dbt manifest. Run dbt to compile it.")
        # depends_on.macros entries look like 'macro.<project>.<name>'.
        suffix = f".{c.macro_name}"
        if not any(uid.endswith(suffix) for uid in node.depends_on_macros):
            return _fail(
                f"Model '{c.model}' doesn't call macro `{c.macro_name}` "
                "(checked via the compiled manifest). Make sure you actually "
                "invoke it in the model — `{{{{ " + c.macro_name + "(...) }}}}`."
            )
        return _ok()

    if c.type == "manifest_macro_defined":
        manifest = _require_manifest()
        if isinstance(manifest, CheckResult):
            return manifest
        if not manifest.find_macro(c.macro_name):
            return _fail(
                f"Macro `{c.macro_name}` not found in the manifest. Define it "
                f"with {{% macro {c.macro_name}(...) %}} in macros/."
            )
        return _ok()

    if c.type == "manifest_snapshot_exists":
        manifest = _require_manifest()
        if isinstance(manifest, CheckResult):
            return manifest
        if not manifest.find_snapshot(c.snapshot_name):
            return _fail(
                f"Snapshot `{c.snapshot_name}` not found in the manifest. "
                "Make sure it's defined under `snapshots:` with the right name."
            )
        return _ok()

    if c.type == "manifest_snapshot_config":
        manifest = _require_manifest()
        if isinstance(manifest, CheckResult):
            return manifest
        snap = manifest.find_snapshot(c.snapshot_name)
        if not snap:
            return _fail(
                f"Snapshot `{c.snapshot_name}` not found in the manifest. "
                "Make sure it's defined in the snapshots/ YAML."
            )
        actual = snap.config.get(c.key)
        if actual is None or actual == "":
            return _fail(
                f"Snapshot `{c.snapshot_name}` has no `{c.key}` configured."
            )
        if str(actual).strip().lower() != c.value.strip().lower():
            return _fail(
                f"Snapshot `{c.snapshot_name}` has {c.key}={actual!r}, expected {c.value!r}."
            )
        return _ok()

    if c.type == "manifest_snapshot_refs":
        manifest = _require_manifest()
        if isinstance(manifest, CheckResult):
            return manifest
        snap = manifest.find_snapshot(c.snapshot_name)
        if not snap:
            return _fail(
                f"Snapshot `{c.snapshot_name}` not found in the manifest. "
                "Make sure it's defined in the snapshots/ YAML."
            )
        suffix = f".{c.target_model}"
        if not any(uid.endswith(suffix) for uid in snap.depends_on):
            return _fail(
                f"Snapshot `{c.snapshot_name}` doesn't reference model "
                f"`{c.target_model}`. Set `relation: ref('{c.target_model}')`."
            )
        return _ok()

    return _fail(f"Unknown check type: {c.type}")


def _require_manifest():
    manifest = artifact_reader.read_manifest()
    if not manifest:
        return _fail(
            "No dbt manifest yet — run dbt (or click 'dbt run') so we can "
            "validate against what dbt actually parsed."
        )
    return manifest


_VALID_FRESHNESS_PERIODS = {"minute", "hour", "day"}


def _validate_freshness_threshold(value: object, key: str) -> str | None:
    """Returns an error reason if the threshold is malformed, else None."""
    if value is None:
        return f"{key} is empty — expected a mapping like {{count: 24, period: hour}}."
    if not isinstance(value, dict):
        return f"{key} must be a mapping with `count` and `period` (got {type(value).__name__})."
    if "count" not in value:
        return f"{key} is missing `count`."
    if "period" not in value:
        return f"{key} is missing `period`."
    count = value["count"]
    period = value["period"]
    if not isinstance(count, int) or count <= 0:
        return f"{key}.count must be a positive integer (got {count!r})."
    if not isinstance(period, str) or period.lower() not in _VALID_FRESHNESS_PERIODS:
        return (
            f"{key}.period must be one of "
            f"{sorted(_VALID_FRESHNESS_PERIODS)} (got {period!r})."
        )
    return None


def _resolve_freshness(node: dict) -> object:
    """dbt accepts freshness at the top level OR inside a `config:` block.
    Either is valid; check both."""
    if not isinstance(node, dict):
        return None
    if "freshness" in node:
        return node["freshness"]
    cfg = node.get("config")
    if isinstance(cfg, dict) and "freshness" in cfg:
        return cfg["freshness"]
    return None


def _has_loaded_at_field(*nodes: object) -> bool:
    """loaded_at_field can live at the top level or under config: too."""
    for node in nodes:
        if not isinstance(node, dict):
            continue
        if node.get("loaded_at_field"):
            return True
        cfg = node.get("config")
        if isinstance(cfg, dict) and cfg.get("loaded_at_field"):
            return True
    return False


def _check_freshness_config(source_name: str, table_name: str) -> CheckResult:
    """Walk the YAML structurally so that comments, malformed blocks, and
    config attached to the wrong source/table can't slip past."""
    candidates: list[Path] = []
    for path in DBT_PROJECT_DIR.rglob("*.yml"):
        if not path.is_file() or "target" in path.parts:
            continue
        candidates.append(path)

    last_reason: str | None = None
    for path in candidates:
        try:
            doc = yaml.safe_load(path.read_text())
        except yaml.YAMLError as e:
            return _fail(f"YAML parse error in {path.name}: {e}")
        if not isinstance(doc, dict):
            continue
        sources = doc.get("sources")
        if not isinstance(sources, list):
            continue
        for src in sources:
            if not isinstance(src, dict) or src.get("name") != source_name:
                continue
            tables = src.get("tables")
            if not isinstance(tables, list):
                continue
            for tbl in tables:
                if not isinstance(tbl, dict) or tbl.get("name") != table_name:
                    continue
                # Found the right source.table — validate it. Freshness can
                # live directly on the table or under a `config:` block;
                # source-level config inherits to tables, so check the
                # source too.
                freshness = _resolve_freshness(tbl) or _resolve_freshness(src)
                if freshness is None or freshness == {}:
                    last_reason = (
                        f"Found `{source_name}.{table_name}` but it has no `freshness:` "
                        "block. Add one (top-level or under `config:`) with `warn_after` "
                        "and `error_after` thresholds."
                    )
                    continue
                if not isinstance(freshness, dict):
                    last_reason = (
                        f"`freshness` on `{source_name}.{table_name}` must be a mapping, "
                        f"got {type(freshness).__name__}."
                    )
                    continue
                missing = [k for k in ("warn_after", "error_after") if k not in freshness]
                if missing:
                    last_reason = (
                        f"`freshness` on `{source_name}.{table_name}` is missing: "
                        f"{', '.join(missing)}."
                    )
                    continue
                bad_threshold = False
                for key in ("warn_after", "error_after"):
                    err = _validate_freshness_threshold(freshness[key], f"freshness.{key}")
                    if err:
                        last_reason = (
                            f"`{source_name}.{table_name}` freshness misconfigured: {err}"
                        )
                        bad_threshold = True
                        break
                if bad_threshold:
                    continue
                if not _has_loaded_at_field(tbl, src):
                    last_reason = (
                        f"`{source_name}.{table_name}` has freshness thresholds but no "
                        "`loaded_at_field` — dbt needs that column to know what to compare."
                    )
                    continue
                return _ok()

    if last_reason:
        return _fail(last_reason)
    return _fail(
        f"No freshness configuration found on source `{source_name}.{table_name}` "
        "in any sources YAML."
    )


def _detect_near_miss(pattern: str, sql: str) -> str | None:
    sql_lower = sql.lower()
    known_types = {
        "int", "integer", "bigint", "smallint",
        "float", "double", "decimal", "numeric",
        "text", "varchar", "char", "string",
        "boolean", "bool",
        "date", "timestamp", "timestamptz", "time", "interval",
    }
    for m in re.finditer(r"cast\s*\(\s*(\w+)\s+as\s+(\w+)\s*\)", sql_lower):
        type_name = m.group(2)
        if type_name not in known_types:
            close = get_close_matches(type_name, known_types, n=1, cutoff=0.6)
            if close:
                return f"cast({m.group(1)} as {type_name}) has a typo — did you mean '{close[0]}'?"
    if "replace" in pattern.lower() and "replace" not in sql_lower and "cast" in sql_lower:
        return "You're casting but may need to clean the value first. Check the hint."
    if "lower" in pattern.lower() and "lower" not in sql_lower and "upper" in sql_lower:
        return "Found upper() but the objective asks for lowercase. Use lower() instead."
    return None
