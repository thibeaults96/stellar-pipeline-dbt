"""Game ata models for Stellar Pipeline CLI."""
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


# Manifest-based checks. These read dbt's compiled manifest.json so we trust
# what dbt itself parsed, instead of regexing the file contents. Requires the
# player to have run any dbt command first (run / build / test / seed all
# refresh manifest.json).

class ManifestModelConfig(BaseModel):
    """Verify a model's compiled config carries the expected key/value.

    `value` is compared as a string (case-insensitive) against the manifest
    entry. Use this for `materialized`, `unique_key`, etc. — anything that's a
    scalar in `{{ config(...) }}`. Falsey manifest values (None / empty) are
    treated as "missing" and reported separately."""
    type: Literal["manifest_model_config"] = "manifest_model_config"
    model: str
    key: str
    value: str


class ManifestModelDescription(BaseModel):
    """Verify a model has a non-empty description in the manifest.

    `min_length` rejects placeholder descriptions like 'x' or 'TODO'. The
    manifest description is what dbt parsed from YAML, so this catches cases
    where the description was attached to the wrong model in YAML."""
    type: Literal["manifest_model_description"] = "manifest_model_description"
    model: str
    min_length: int = 10


class ManifestColumnDescription(BaseModel):
    """Verify a column on a model has a non-empty description in the manifest."""
    type: Literal["manifest_column_description"] = "manifest_column_description"
    model: str
    column: str
    min_length: int = 10


class ManifestColumnTest(BaseModel):
    """Verify a model.column has a test of the given name attached in the
    manifest. For accepted_values, optionally enforce that the values list
    includes everything in `required_values` and excludes everything in
    `forbidden_values`. This catches the common false-pass where a player
    writes an accepted_values block with the wrong list and the regex check
    is satisfied because *some* list exists."""
    type: Literal["manifest_column_test"] = "manifest_column_test"
    model: str
    column: str
    test_name: str
    required_values: list[str] = Field(default_factory=list)
    forbidden_values: list[str] = Field(default_factory=list)


class ManifestModelDependsOnMacro(BaseModel):
    """Verify a model's compiled depends_on.macros references the named macro.
    Use this instead of regexing for `macro_name(` — manifest tracks the
    actual call graph after Jinja resolution, so a macro name in a comment
    can't satisfy this check."""
    type: Literal["manifest_model_depends_on_macro"] = "manifest_model_depends_on_macro"
    model: str
    macro_name: str


class ManifestMacroDefined(BaseModel):
    """Verify a macro is defined and parsed into manifest.macros."""
    type: Literal["manifest_macro_defined"] = "manifest_macro_defined"
    macro_name: str


class ManifestSnapshotExists(BaseModel):
    """Verify a snapshot of the given name appears in the dbt manifest, i.e.
    dbt successfully parsed and registered it."""
    type: Literal["manifest_snapshot_exists"] = "manifest_snapshot_exists"
    snapshot_name: str


class ManifestSnapshotConfig(BaseModel):
    """Verify a snapshot exists with the expected config key/value, parsed
    structurally by dbt. Replaces YAML regex matching for snapshots."""
    type: Literal["manifest_snapshot_config"] = "manifest_snapshot_config"
    snapshot_name: str
    key: str
    value: str


class ManifestSnapshotRefs(BaseModel):
    """Verify a snapshot in the manifest depends on a specific model (i.e.
    its `relation:` was wired up via ref())."""
    type: Literal["manifest_snapshot_refs"] = "manifest_snapshot_refs"
    snapshot_name: str
    target_model: str


class GitStateCheck(BaseModel):
    """Read a boolean field off GameState.git — committed, pr_opened, merged.
    Used by the Deploy level to gate on the player's simulated git flow."""
    type: Literal["git_state"] = "git_state"
    key: str  # one of: staged, committed, pr_opened, ci_passing, merged


class ScheduleStateCheck(BaseModel):
    """Verify the player has configured a job schedule of a specific kind, or
    has triggered at least N simulated scheduled runs."""
    type: Literal["schedule_state"] = "schedule_state"
    kind: str | None = None  # None means any kind matches; otherwise: manual / interval / cron / on_merge
    min_runs: int = 0  # minimum scheduled-run count required to pass


class EnvironmentStateCheck(BaseModel):
    """Verify a field on the simulated production environment is set
    (non-empty / non-zero). Used by the Set Up Production level."""
    type: Literal["environment_state"] = "environment_state"
    key: str  # one of: name, target_schema, threads, dbt_version


class ScheduleCommandsCheck(BaseModel):
    """Verify the player's scheduled command list contains specific dbt
    sub-commands and/or has at least N commands total."""
    type: Literal["schedule_commands"] = "schedule_commands"
    required: list[str] = Field(default_factory=list)  # e.g. ['dbt build', 'dbt source freshness']
    min_count: int = 0


class ScheduleEnvironmentCheck(BaseModel):
    """Verify the job is pointed at the named environment."""
    type: Literal["schedule_environment"] = "schedule_environment"


ObjectiveCheck = Union[
    HasColumnAlias, HasRefCall, FileContainsActiveSql, FileContains,
    NoHardcodedRefs, HasTest, HasFreshnessConfig,
    ArtifactAllModelsPass, ArtifactModelPasses, ArtifactTestRanWithFailures,
    SourceFreshnessRan,
    DuckDBColumnExists, DuckDBColumnsExist, DuckDBColumnValuesCheck, DuckDBRowCount, SnapshotRan,
    ManifestModelConfig, ManifestModelDescription, ManifestColumnDescription,
    ManifestColumnTest, ManifestModelDependsOnMacro, ManifestMacroDefined,
    ManifestSnapshotExists, ManifestSnapshotConfig, ManifestSnapshotRefs,
    GitStateCheck, ScheduleStateCheck,
    EnvironmentStateCheck, ScheduleCommandsCheck, ScheduleEnvironmentCheck,
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
    event: Union[str, list[str]]
    narrative_key: str
    once: bool = True
    # Objective IDs that must already be in the player's completed set before
    # this trigger can fire. Use this to gate "you've done X and Y" narratives
    # on multiple objectives without needing a synthetic combined event.
    requires: list[str] = Field(default_factory=list)

class BadgeDefinition(BaseModel):
    id: str
    emoji: str
    name: str
    description: str
    xp: int


# ─── Quiz ─────────────────────────────────────────────────────────────────────

class QuizQuestion(BaseModel):
    """A single multiple-choice quiz question shown between levels.

    `correct` is the 0-based index into `options`. `explanation` is shown after
    the player answers (right or wrong) so the quiz reinforces the concept
    instead of just grading it."""
    question: str
    options: list[str]
    correct: int
    explanation: str = ""


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
    quiz: list[QuizQuestion] = Field(default_factory=list)


# ─── Game State (persisted to JSON) ──────────────────────────────────────────

class EarnedBadge(BaseModel):
    id: str
    emoji: str
    name: str
    level_id: int

class GitState(BaseModel):
    """Simulated git promotion state used by the Deploy level (L7).
    Pure game state — we don't actually run git. Tracks the player's
    progression through stage → commit → PR → merge."""
    branch: str = "feature/deploy-pipeline"
    staged: bool = False
    committed: bool = False
    commit_message: str = ""
    pr_opened: bool = False
    ci_passing: bool = False
    merged: bool = False


class EnvironmentState(BaseModel):
    """Simulated production environment used by the Set Up Production level
    (L8). Mirrors what a dbt platform deployment environment looks like:
    name + git branch + target schema + threads + pinned dbt version. The
    DuckDB target underneath is always the same — this is metadata the
    player configures, which the Schedule level then points jobs at."""
    name: str = ""
    git_branch: str = ""
    target_schema: str = ""
    threads: int = 0
    dbt_version: str = ""


class ScheduleState(BaseModel):
    """Simulated job state used by the Schedule level (L9).
    kind is one of: '', 'manual', 'interval', 'cron', 'on_merge'.
    commands is the ordered list of dbt commands the job runs (e.g.
    ['dbt seed', 'dbt build', 'dbt source freshness']).
    environment_name is the environment the job runs against — populated
    from EnvironmentState in L8."""
    kind: str = ""
    expression: str = ""  # cron expression or interval ("6h") — meaning depends on kind
    commands: list[str] = Field(default_factory=list)
    environment_name: str = ""
    run_count: int = 0
    last_run_output: str = ""


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
    git: GitState = Field(default_factory=GitState)
    environment: EnvironmentState = Field(default_factory=EnvironmentState)
    schedule: ScheduleState = Field(default_factory=ScheduleState)
