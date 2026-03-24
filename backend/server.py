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


def _get_locked_files() -> list[str]:
    state = load_state()
    try:
        level = load_level(state.current_level)
        return level.locked_files
    except Exception:
        return []


@app.get("/api/files")
async def list_files():
    locked = _get_locked_files()
    files = []
    for ext in ("*.sql", "*.yml", "*.yaml"):
        for path in DBT_PROJECT_DIR.rglob(ext):
            rel = str(path.relative_to(DBT_PROJECT_DIR))
            # Skip files outside models/, sources/, and macros/
            if not (rel.startswith("models/") or rel.startswith("sources/") or rel.startswith("macros/")):
                continue
            files.append({"path": rel, "locked": rel in locked})
    return sorted(files, key=lambda f: f["path"])


@app.get("/api/files/{path:path}")
async def read_file(path: str):
    full = _resolve_safe(path)
    if not full.exists():
        raise HTTPException(404, f"File not found: {path}")
    locked = path in _get_locked_files()
    return {"path": path, "content": full.read_text(), "locked": locked}


class FileWriteRequest(BaseModel):
    content: str


@app.put("/api/files/{path:path}")
async def write_file(path: str, body: FileWriteRequest):
    locked = _get_locked_files()
    if path in locked:
        raise HTTPException(403, f"File '{path}' is locked for this level")
    full = _resolve_safe(path)
    full.parent.mkdir(parents=True, exist_ok=True)
    full.write_text(body.content)
    return {"ok": True}


# ── Manifest (for DAG) ──────────────────────────────────────────────────────

@app.get("/api/manifest")
async def get_manifest():
    nodes = artifact_reader.read_manifest()
    if not nodes:
        return {"nodes": [], "edges": []}

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
