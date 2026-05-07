"""Game ata models for Stellar Pipeline CLI."""
from __fudture__ import annotations

from typing import Any, Literal, Optional, Union
from pydantic import BaseModel, Field


# ─── Objective Check Types ────────────────────────────────────────────────────
# File-content checks (no dbt run needed)

class HasColumnAlias(BaseModel):
    type: Literal["has_column_alias"] = "has_column_alias"
    filename: str
    aliases: list[str]

class HasRefCall(BaseModel):
    type: Literal["has_ref_call"] = "has_ref_call"
    filename: str
    target_model: str

class FileContainsActiveSql(BaseModel):
    type: Literal["file_contains_active_sql"] = "file_contains_active_sql"
    filename: str
    pattern: str

class FileContains(BaseModel):
    type: Literal["file_contains"] = "file_contains"
    filename: str
    pattern: str

class NoHardcodedRefs(BaseModel):
    type: Literal["no_hardcoded_refs"] = "no_hardcoded_refs"
    filename: str

class HasTest(BaseModel):
    type: Literal["has_test"] = "has_test"
    model_name: str
    column_name: str
    test_type: str

class HasFreshnessConfig(BaseModel):
    type: Literal["has_freshness_config"] = "has_freshness_config"
    source_name: str
    table_name: str

# Artifact-based checks (require dbt run/test)

class ArtifactAllModelsPass(BaseModel):
    type: Literal["all_models_pass"] = "all_models_pass"

class ArtifactModelPasses(BaseModel):
    type: Literal["model_passes"] = "model_passes"
    model: str

class ArtifactTestRanWithFailures(BaseModel):
    type: Literal["tests_ran_with_failures"] = "tests_ran_with_failures"

class SourceFreshnessRan(BaseModel):
    """Check that `dbt source freshness` actually ran against this source —
    proves the freshness config is structurally valid because dbt accepted
    and executed it. Status of pass/warn/error is fine; only `runtime error`
    counts as a failure (config or query was bad)."""
    type: Literal["source_freshness_ran"] = "source_freshness_ran"
    source_name: str
    table_name: str

# DuckDB query check
class DuckDBColumnExists(BaseModel):
    type: Literal["duckdb_column_exists"] = "duckdb_column_exists"
    table: str
    column: str
    schema_name: str = "main"

class DuckDBColumnsExist(BaseModel):
    """Check that specific columns exist in a model's output with optional type checking."""
    type: Literal["duckdb_columns_exist"] = "duckdb_columns_exist"
    table: str
    columns: list[str]
    types: dict[str, str] = {}  # column_name -> expected type (e.g. "INTEGER", "TIMESTAMP")

class DuckDBColumnValuesCheck(BaseModel):
    """Check that column values match a condition (e.g. all lowercase, all equal to X)."""
    type: Literal["duckdb_column_values"] = "duckdb_column_values"
    table: str
    query: str  # SQL condition that should return 0 rows (no violations)

class SnapshotRan(BaseModel):
    """Check that a snapshot table exists in DuckDB (meaning dbt snapshot was run)."""
    type: Literal["snapshot_ran"] = "snapshot_ran"
    table: str

class DuckDBRowCount(BaseModel):
    """Check that a model has rows and optionally that all rows match a condition."""
    type: Literal["duckdb_row_count"] = "duckdb_row_count"
    table: str
    min_rows: int = 1
    where: str = ""  # Optional WHERE clause — all rows must match


ObjectiveCheck = Union[
    HasColumnAlias, HasRefCall, FileContainsActiveSql, FileContains,
    NoHardcodedRefs, HasTest, HasFreshnessConfig,
    ArtifactAllModelsPass, ArtifactModelPasses, ArtifactTestRanWithFailures,
    SourceFreshnessRan,
    DuckDBColumnExists, DuckDBColumnsExist, DuckDBColumnValuesCheck, DuckDBRowCount, SnapshotRan,
]


# ─── Objective Definition ─────────────────────────────────────────────────────

class ObjectiveDefinition(BaseModel):
    id: str
    label: str
    hint: str = ""
    check: ObjectiveCheck


# ─── Narrative ────────────────────────────────────────────────────────────────

class NarrativeEvent(BaseModel):
    id: str
    character: str
    message: str
    priority: Literal["low", "normal", "high"] = "normal"

class NarrativeTrigger(BaseModel):
    id: str
    event: str
    narrative_key: str
    once: bool = True

class BadgeDefinition(BaseModel):
    id: str
    emoji: str
    name: str
    description: str
    xp: int


# ─── Level Config ─────────────────────────────────────────────────────────────

class LevelConfig(BaseModel):
    id: int
    title: str
    subtitle: str
    character: str
    xp_reward: int
    badge: BadgeDefinition
    objectives: list[ObjectiveDefinition]
    narrative_triggers: list[NarrativeTrigger]
    narrative_script: dict[str, NarrativeEvent]
    initial_files: dict[str, str] = Field(default_factory=dict)
    locked_files: list[str] = Field(default_factory=list)
    seed_files: dict[str, str] = Field(default_factory=dict)


# ─── Game State (persisted to JSON) ──────────────────────────────────────────

class EarnedBadge(BaseModel):
    id: str
    emoji: str
    name: str
    level_id: int

class GameState(BaseModel):
    current_level: int = 1
    total_xp: int = 0
    earned_badges: list[EarnedBadge] = Field(default_factory=list)
    completed_levels: list[int] = Field(default_factory=list)
    completed_objectives: dict[int, list[str]] = Field(default_factory=dict)
    fired_triggers: dict[int, list[str]] = Field(default_factory=dict)
    run_count: int = 0
    test_count: int = 0
    pending_narratives: list[dict] = Field(default_factory=list)
