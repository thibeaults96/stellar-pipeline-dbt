"""Convert game engine objects to JSON-serializable dicts."""
from __future__ import annotations

from stellar_dbt.engine.game_engine import ActionReport
from stellar_dbt.models.game_types import GameState, LevelConfig, ObjectiveDefinition, NarrativeEvent


def serialize_objectives(
    objectives: list[tuple[ObjectiveDefinition, bool, str | None]],
) -> list[dict]:
    return [
        {
            "id": obj.id,
            "label": obj.label,
            "hint": obj.hint,
            "passed": passed,
            "reason": reason,
        }
        for obj, passed, reason in objectives
    ]


def serialize_narrative(event: NarrativeEvent) -> dict:
    return event.model_dump()


def serialize_report(report: ActionReport) -> dict:
    return {
        "dbtOutput": report.dbt_output,
        "dbtSuccess": report.dbt_success,
        "objectives": serialize_objectives(report.objectives),
        "newlyCompleted": report.newly_completed,
        "narratives": [serialize_narrative(n) for n in report.narratives],
        "levelComplete": report.level_complete,
        "badge": report.badge.model_dump() if report.badge else None,
        "xpEarned": report.xp_earned,
    }


def serialize_status(
    state: GameState,
    level: LevelConfig,
    objectives: list[tuple[ObjectiveDefinition, bool, str | None]],
) -> dict:
    return {
        "currentLevel": state.current_level,
        "totalXP": state.total_xp,
        "earnedBadges": [b.model_dump() for b in state.earned_badges],
        "completedLevels": state.completed_levels,
        "runCount": state.run_count,
        "testCount": state.test_count,
        "level": {
            "id": level.id,
            "title": level.title,
            "subtitle": level.subtitle,
            "character": level.character,
            "xpReward": level.xp_reward,
        },
        "objectives": serialize_objectives(objectives),
        "pendingNarratives": state.pending_narratives,
    }
