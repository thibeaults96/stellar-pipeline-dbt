"""Check objectives against real dbt artifacts, files, and DuckDB."""
from __future__ import annotations

import re
from dataclasses import dataclass
from difflib import get_close_matches
from pathlib import Path

import duckdb

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
        for path in DBT_PROJECT_DIR.rglob("*.yml"):
            if not path.is_file() or "target" in path.parts:
                continue
            text = path.read_text()
            if f"name: {c.source_name}" in text and f"name: {c.table_name}" in text and "freshness" in text:
                if "warn_after" in text and "error_after" in text:
                    return _ok()
                missing = []
                if "warn_after" not in text:
                    missing.append("warn_after")
                if "error_after" not in text:
                    missing.append("error_after")
                return _fail(f"Freshness block found but missing: {', '.join(missing)}.")
        return _fail(f"No freshness configuration found for source '{c.source_name}.{c.table_name}'.")

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

    return _fail(f"Unknown check type: {c.type}")


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
