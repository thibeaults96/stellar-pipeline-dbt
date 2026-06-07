"""FastAPI server — thin HTTP layer over the game engine."""
from __future__ import annotations

from pathlib import Path

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

import csv
import io

from stellar_dbt.config import DBT_PROJECT_DIR, DB_PATH
from stellar_dbt.engine.game_engine import GameEngine
from stellar_dbt.engine.state_manager import load_state, save_state
from stellar_dbt.engine import artifact_reader
from stellar_dbt.levels.loader import load_level, list_levels
from backend.serializers import serialize_report, serialize_status

app = FastAPI(title="Stellar Pipeline API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://127.0.0.1:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ── Status ───────────────────────────────────────────────────────────────────

@app.get("/api/status")
async def get_status():
    state, level, objectives = GameEngine.status()
    result = serialize_status(state, level, objectives)
    # Clear pending narratives after delivering them
    if state.pending_narratives:
        state.pending_narratives = []
        save_state(state)
    return result


# ── Actions ──────────────────────────────────────────────────────────────────

@app.post("/api/start/{level_id}")
async def start_level(level_id: int):
    try:
        report = GameEngine.start_level(level_id)
    except ValueError as e:
        raise HTTPException(404, str(e))
    return serialize_report(report)


@app.post("/api/run")
async def run_dbt():
    report = GameEngine.run()
    return serialize_report(report)


@app.post("/api/test")
async def test_dbt():
    report = GameEngine.test()
    return serialize_report(report)


@app.post("/api/build")
async def build_dbt():
    report = GameEngine.build()
    return serialize_report(report)


@app.post("/api/snapshot")
async def snapshot_dbt():
    report = GameEngine.snapshot()
    return serialize_report(report)


@app.post("/api/seed")
async def seed_dbt():
    report = GameEngine.seed()
    return serialize_report(report)


@app.post("/api/deps")
async def deps_dbt():
    report = GameEngine.deps()
    return serialize_report(report)


@app.post("/api/freshness")
async def freshness_dbt():
    report = GameEngine.freshness()
    return serialize_report(report)


# ── Deploy (L7) ─────────────────────────────────────────────────────────────


class GitCommitRequest(BaseModel):
    message: str = ""


@app.get("/api/git")
async def get_git_state():
    state = load_state()
    return state.git.model_dump()


@app.post("/api/git/stage")
async def git_stage():
    report = GameEngine.git_stage()
    return serialize_report(report)


@app.post("/api/git/commit")
async def git_commit(body: GitCommitRequest):
    if not body.message.strip():
        raise HTTPException(400, "Commit message can't be empty.")
    report = GameEngine.git_commit(body.message.strip())
    return serialize_report(report)


@app.post("/api/git/pr")
async def git_pr():
    state = load_state()
    if not state.git.committed:
        raise HTTPException(400, "Commit your changes before opening a PR.")
    report = GameEngine.git_open_pr()
    return serialize_report(report)


@app.post("/api/git/merge")
async def git_merge():
    state = load_state()
    if not state.git.pr_opened:
        raise HTTPException(400, "Open a PR before merging.")
    if not state.git.ci_passing:
        raise HTTPException(400, "CI hasn't passed — run dbt build until it's green.")
    report = GameEngine.git_merge()
    return serialize_report(report)


# ── Environment (L8) ────────────────────────────────────────────────────────


class EnvironmentSetRequest(BaseModel):
    name: str | None = None
    git_branch: str | None = None
    target_schema: str | None = None
    threads: int | None = None
    dbt_version: str | None = None


@app.get("/api/env")
async def get_env_state():
    state = load_state()
    return state.environment.model_dump()


@app.post("/api/env")
async def env_set(body: EnvironmentSetRequest):
    if body.threads is not None and (body.threads < 1 or body.threads > 32):
        raise HTTPException(400, "threads must be between 1 and 32")
    report = GameEngine.env_set(
        name=body.name,
        git_branch=body.git_branch,
        target_schema=body.target_schema,
        threads=body.threads,
        dbt_version=body.dbt_version,
    )
    return serialize_report(report)


# ── Schedule (L9) ───────────────────────────────────────────────────────────


_VALID_SCHEDULE_KINDS = {"manual", "interval", "cron", "on_merge"}


class ScheduleSetRequest(BaseModel):
    kind: str | None = None
    expression: str | None = None
    commands: list[str] | None = None
    environment_name: str | None = None


@app.get("/api/schedule")
async def get_schedule_state():
    state = load_state()
    return state.schedule.model_dump()


@app.post("/api/schedule")
async def schedule_set(body: ScheduleSetRequest):
    if body.kind is not None and body.kind not in _VALID_SCHEDULE_KINDS:
        raise HTTPException(400, f"Unknown schedule kind: {body.kind}")
    report = GameEngine.schedule_set(
        kind=body.kind,
        expression=body.expression,
        commands=body.commands,
        environment_name=body.environment_name,
    )
    return serialize_report(report)


@app.post("/api/schedule/trigger")
async def schedule_trigger():
    state = load_state()
    if not state.schedule.kind:
        raise HTTPException(400, "Pick a schedule kind first.")
    report = GameEngine.schedule_trigger()
    return serialize_report(report)


@app.post("/api/check")
async def check_objectives():
    report = GameEngine.check_objectives()
    return serialize_report(report)


@app.post("/api/reset")
async def reset_level():
    state = load_state()
    level_id = state.current_level
    state.completed_objectives.pop(level_id, None)
    state.fired_triggers.pop(level_id, None)
    state.pending_narratives = []
    state.run_count = 0
    state.test_count = 0
    state.total_xp = 0
    state.earned_badges = []
    # Clear the Deploy/Env/Schedule simulation state on level reset so
    # re-entering those levels starts from a clean slate.
    state.git = state.git.__class__()
    state.environment = state.environment.__class__()
    state.schedule = state.schedule.__class__()
    if level_id in state.completed_levels:
        state.completed_levels.remove(level_id)
    save_state(state)
    # Clear stale DuckDB so seeds get re-created on next run
    if DB_PATH.exists():
        DB_PATH.unlink()
    report = GameEngine.start_level(level_id)
    return serialize_report(report)


# ── Levels ───────────────────────────────────────────────────────────────────

@app.get("/api/levels")
async def get_levels():
    state = load_state()
    levels = list_levels()
    for lvl in levels:
        lvl["completed"] = lvl["id"] in state.completed_levels
        lvl["current"] = lvl["id"] == state.current_level
    return levels


# ── Quiz ─────────────────────────────────────────────────────────────────────

@app.get("/api/quiz/{level_id}")
async def get_quiz(level_id: int):
    """Return the quiz questions for a level (empty list if none defined).
    Used by the frontend to show a short check-for-understanding between
    levels — non-blocking, never gates progression."""
    try:
        level = load_level(level_id)
    except ValueError as e:
        raise HTTPException(404, str(e))
    return {
        "levelId": level.id,
        "levelTitle": level.title,
        "questions": [q.model_dump() for q in level.quiz],
    }


# ── Hints ────────────────────────────────────────────────────────────────────

@app.get("/api/hints/{objective_id}")
async def get_hint(objective_id: str):
    state = load_state()
    level = load_level(state.current_level)
    obj = next((o for o in level.objectives if o.id == objective_id), None)
    if not obj:
        raise HTTPException(404, f"Objective '{objective_id}' not found")
    return {"id": obj.id, "label": obj.label, "hint": obj.hint}


# ── Files ────────────────────────────────────────────────────────────────────

def _resolve_safe(rel_path: str) -> Path:
    """Resolve a relative path under DBT_PROJECT_DIR safely."""
    # Reject absolute paths and traversal attempts
    if rel_path.startswith("/") or rel_path.startswith("\\") or ".." in rel_path:
        raise HTTPException(400, "Invalid path")
    full = (DBT_PROJECT_DIR / rel_path).resolve()
    # Belt-and-suspenders: verify resolved path is inside the project
    if not full.is_relative_to(DBT_PROJECT_DIR.resolve()):
        raise HTTPException(400, "Invalid path")
    return full


# Folders the player owns — files inside are writable by default, locked only
# when the level explicitly lists them in locked_files.
_PROJECT_DIRS = ("models/", "macros/", "snapshots/")

# Files outside the project dirs that we still want visible in the tree so the
# narrative matches a real dbt project layout. profiles.yml and the seed CSVs
# are always read-only — players inspect them, they don't edit them.
_ALWAYS_LOCKED_PATHS = {"profiles.yml"}
_EXTRA_PATTERNS = ("dbt_project.yml", "profiles.yml", "seeds/*.csv")


def _get_locked_files() -> list[str]:
    state = load_state()
    try:
        level = load_level(state.current_level)
        return level.locked_files
    except Exception:
        return []


def _editable_extras_for_current_level() -> set[str]:
    """Files outside the project dirs that the current level explicitly ships
    via initial_files — those are the only non-project files the player can
    edit (e.g. L7 ships dbt_project.yml so the player can configure
    materializations)."""
    state = load_state()
    try:
        level = load_level(state.current_level)
    except Exception:
        return set()
    return {
        path for path in level.initial_files.keys()
        if not path.startswith(_PROJECT_DIRS) and path not in _ALWAYS_LOCKED_PATHS
    }


def _is_locked(rel: str, locked: list[str], editable_extras: set[str]) -> bool:
    if rel in locked:
        return True
    if rel in _ALWAYS_LOCKED_PATHS:
        return True
    if rel.startswith("seeds/"):
        return True
    if rel.startswith(_PROJECT_DIRS):
        return False
    # Anything else outside the project dirs is locked unless the level ships it.
    return rel not in editable_extras


@app.get("/api/files")
async def list_files():
    locked = _get_locked_files()
    editable_extras = _editable_extras_for_current_level()
    files = []
    seen: set[str] = set()

    # Project dirs (models/, macros/, snapshots/) — full tree, includes .md doc blocks.
    for ext in ("*.sql", "*.yml", "*.yaml", "*.md"):
        for path in DBT_PROJECT_DIR.rglob(ext):
            rel = str(path.relative_to(DBT_PROJECT_DIR))
            if not rel.startswith(_PROJECT_DIRS):
                continue
            if rel in seen:
                continue
            seen.add(rel)
            files.append({"path": rel, "locked": _is_locked(rel, locked, editable_extras)})

    # Root config + seeds — show even when read-only so the player sees the full project.
    for pattern in _EXTRA_PATTERNS:
        for path in DBT_PROJECT_DIR.glob(pattern):
            rel = str(path.relative_to(DBT_PROJECT_DIR))
            if rel in seen:
                continue
            seen.add(rel)
            files.append({"path": rel, "locked": _is_locked(rel, locked, editable_extras)})

    return sorted(files, key=lambda f: f["path"])


@app.get("/api/files/{path:path}")
async def read_file(path: str):
    full = _resolve_safe(path)
    if not full.exists():
        raise HTTPException(404, f"File not found: {path}")
    locked = _is_locked(path, _get_locked_files(), _editable_extras_for_current_level())
    return {"path": path, "content": full.read_text(), "locked": locked}


class FileWriteRequest(BaseModel):
    content: str


@app.put("/api/files/{path:path}")
async def write_file(path: str, body: FileWriteRequest):
    if _is_locked(path, _get_locked_files(), _editable_extras_for_current_level()):
        raise HTTPException(403, f"File '{path}' is locked for this level")
    full = _resolve_safe(path)
    full.parent.mkdir(parents=True, exist_ok=True)
    full.write_text(body.content)
    return {"ok": True}


# ── Manifest (for DAG) ──────────────────────────────────────────────────────

@app.get("/api/manifest")
async def get_manifest():
    manifest = artifact_reader.read_manifest()
    if not manifest:
        return {"nodes": [], "edges": []}
    nodes = manifest.nodes

    # Get run results for status coloring
    rr = artifact_reader.read_run_results()
    status_map: dict[str, str] = {}
    if rr:
        for r in rr.results:
            status_map[r.unique_id] = r.status

    # Seeds and sources represent the same tables — only show sources
    # (they're the logical entry point in the DAG)
    skip_ids = set()
    for uid, node in nodes.items():
        if node.resource_type in ("test", "seed"):
            skip_ids.add(uid)

    serialized_nodes = []
    edges = []
    for uid, node in nodes.items():
        if uid in skip_ids:
            continue
        serialized_nodes.append({
            "id": uid,
            "name": node.name,
            "type": node.resource_type,
            "status": status_map.get(uid, "pending"),
        })
        for dep in node.depends_on:
            if dep in skip_ids:
                continue
            if dep in nodes:
                edges.append({"source": dep, "target": uid})

    return {"nodes": serialized_nodes, "edges": edges}


# ── Source Data Preview ──────────────────────────────────────────────────────

@app.get("/api/sources")
async def list_sources():
    """List available source tables from seed CSVs."""
    seeds_dir = DBT_PROJECT_DIR / "seeds"
    sources = []
    for csv_file in sorted(seeds_dir.glob("*.csv")):
        name = csv_file.stem
        # Count rows (header excluded)
        lines = csv_file.read_text().strip().split("\n")
        row_count = max(0, len(lines) - 1)
        sources.append({"name": name, "rowCount": row_count})
    return sources


@app.get("/api/sources/{name}")
async def preview_source(name: str, limit: int = 50):
    """Preview source data. Tries DuckDB first, falls back to CSV."""
    # Try querying DuckDB for live data
    if DB_PATH.exists():
        try:
            import duckdb
            conn = duckdb.connect(str(DB_PATH), read_only=True)
            cols = conn.execute(
                "SELECT column_name FROM information_schema.columns WHERE table_name = ? AND table_schema = 'main' ORDER BY ordinal_position",
                [name],
            ).fetchall()
            if cols:
                columns = [c[0] for c in cols]
                rows = conn.execute(f'SELECT * FROM main."{name}" LIMIT ?', [limit]).fetchall()
                total = conn.execute(f'SELECT count(*) FROM main."{name}"').fetchone()[0]
                conn.close()
                return {
                    "name": name,
                    "columns": columns,
                    "rows": [dict(zip(columns, row)) for row in rows],
                    "totalRows": total,
                }
            conn.close()
        except Exception:
            pass

    # Fall back to reading the seed CSV directly
    csv_path = DBT_PROJECT_DIR / "seeds" / f"{name}.csv"
    if not csv_path.exists():
        raise HTTPException(404, f"Source '{name}' not found")

    reader = csv.DictReader(io.StringIO(csv_path.read_text()))
    rows = []
    for i, row in enumerate(reader):
        if i >= limit:
            break
        rows.append(row)

    return {
        "name": name,
        "columns": list(rows[0].keys()) if rows else [],
        "rows": rows,
        "totalRows": len(rows),
    }


# ── Model Preview (query results) ───────────────────────────────────────────

@app.get("/api/preview/{model_name}")
async def preview_model(model_name: str, limit: int = 50):
    """Query a built model's results from DuckDB."""
    if not DB_PATH.exists():
        raise HTTPException(400, "No database yet. Run 'dbt run' first.")
    try:
        import duckdb
        conn = duckdb.connect(str(DB_PATH), read_only=True)
        # Check if the table/view exists
        exists = conn.execute(
            "SELECT 1 FROM information_schema.tables WHERE table_name = ? AND table_schema = 'main'",
            [model_name],
        ).fetchone()
        if not exists:
            conn.close()
            raise HTTPException(404, f"Model '{model_name}' not found. Run 'dbt run' to build it.")
        cols = conn.execute(
            "SELECT column_name FROM information_schema.columns WHERE table_name = ? AND table_schema = 'main' ORDER BY ordinal_position",
            [model_name],
        ).fetchall()
        columns = [c[0] for c in cols]
        rows = conn.execute(f'SELECT * FROM main."{model_name}" LIMIT ?', [limit]).fetchall()
        total = conn.execute(f'SELECT count(*) FROM main."{model_name}"').fetchone()[0]
        conn.close()
        return {
            "name": model_name,
            "columns": columns,
            "rows": [dict(zip(columns, row)) for row in rows],
            "totalRows": total,
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(500, f"Query failed: {e}")
