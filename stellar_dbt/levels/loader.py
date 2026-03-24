"""Load level definitions from YAML and apply them to the dbt project."""
from __future__ import annotations

import shutil
from pathlib import Path

import yaml

from stellar_dbt.config import DBT_PROJECT_DIR, DB_PATH, LEVELS_DIR
from stellar_dbt.models.game_types import LevelConfig
from stellar_dbt.engine import dbt_runner


def load_level(level_id: int) -> LevelConfig:
    path = LEVELS_DIR / f"level_{level_id:02d}.yml"
    if not path.exists():
        raise ValueError(f"Level {level_id} not found at {path}")
    data = yaml.safe_load(path.read_text())
    return LevelConfig(**data)


def list_levels() -> list[dict]:
    levels = []
    for path in sorted(LEVELS_DIR.glob("level_*.yml")):
        data = yaml.safe_load(path.read_text())
        levels.append({"id": data["id"], "title": data["title"]})
    return levels


def apply_level(level: LevelConfig) -> None:
    """Write level files to the dbt project and re-seed if needed."""
    # Clear stale artifacts and database so level transitions are clean
    target_dir = DBT_PROJECT_DIR / "target"
    if target_dir.exists():
        shutil.rmtree(target_dir)
    if DB_PATH.exists():
        DB_PATH.unlink()

    # Clean models and macros directories completely then rebuild from initial_files.
    # This prevents leftover files from other levels breaking things.
    for dirname in ("models", "macros"):
        d = DBT_PROJECT_DIR / dirname
        if d.exists():
            shutil.rmtree(d)
    (DBT_PROJECT_DIR / "models").mkdir()

    # Restore base files that every level needs (stg_planets is always the reference)
    _write_base_files()

    # Write seed files if the level has custom seeds
    for filename, content in level.seed_files.items():
        seed_path = DBT_PROJECT_DIR / "seeds" / filename
        seed_path.write_text(content)

    # Write initial model/config files (level-specific)
    for rel_path, content in level.initial_files.items():
        full_path = DBT_PROJECT_DIR / rel_path
        full_path.parent.mkdir(parents=True, exist_ok=True)
        full_path.write_text(content)


def _write_base_files() -> None:
    """Write files that exist in every level (sources, stg_planets)."""
    sources_dir = DBT_PROJECT_DIR / "models" / "sources"
    sources_dir.mkdir(parents=True, exist_ok=True)

    staging_dir = DBT_PROJECT_DIR / "models" / "staging"
    staging_dir.mkdir(parents=True, exist_ok=True)

    marts_dir = DBT_PROJECT_DIR / "models" / "marts"
    marts_dir.mkdir(parents=True, exist_ok=True)

    # Source definition (Level 1 default — levels can override via initial_files)
    (sources_dir / "federation_sources.yml").write_text("""version: 2

sources:
  - name: federation
    description: "Raw telemetry data from Federation sensor arrays"
    schema: main
    tables:
      - name: raw_shipments
        description: "Cargo shipment records from all registered vessels"
      - name: raw_planets
        description: "Planetary registry and resource data"
""")

    # stg_planets (always locked, always the same)
    (staging_dir / "stg_planets.sql").write_text("""-- stg_planets.sql
-- Federation staging model: planetary registry

with source as (

    select * from {{ source('federation', 'raw_planets') }}

),

renamed as (

    select
        planet_id,
        planet_name,
        sector,
        cast(population as bigint) as population,
        is_federation_member

    from source

)

select * from renamed
""")
