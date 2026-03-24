"""Game data models for Stellar Pipeline CLI."""
from __future__ import annotations

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

# DuckDB query check
class DuckDBColumnExists(BaseModel):
    type: Literal["duckdb_column_exists"] = "duckdb_column_exists"
    table: str
    column: str
    schema_name: str = "main"


ObjectiveCheck = Union[
    HasColumnAlias, HasRefCall, FileContainsActiveSql, FileContains,
    NoHardcodedRefs, HasTest, HasFreshnessConfig,
    ArtifactAllModelsPass, ArtifactModelPasses, ArtifactTestRanWithFailures,
    DuckDBColumnExists,
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
