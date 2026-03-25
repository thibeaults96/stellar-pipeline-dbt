"""Central game orchestrator — wraps dbt commands with game logic."""
from __future__ import annotations

from dataclasses import dataclass, field

from stellar_dbt.models.game_types import (
    GameState, LevelConfig, EarnedBadge, NarrativeEvent, ObjectiveDefinition,
)
from stellar_dbt.engine import dbt_runner, artifact_reader, objective_checker, narrative_engine
from stellar_dbt.engine.state_manager import load_state, save_state
from stellar_dbt.levels.loader import load_level, apply_level


@dataclass
class ActionReport:
    """Result of a game action (run/test/check) for the CLI to render."""
    dbt_output: str = ""
    dbt_success: bool = True
    objectives: list[tuple[ObjectiveDefinition, bool, str | None]] = field(default_factory=list)
    newly_completed: list[str] = field(default_factory=list)
    narratives: list[NarrativeEvent] = field(default_factory=list)
    level_complete: bool = False
    badge: EarnedBadge | None = None
    xp_earned: int = 0


class GameEngine:

    @staticmethod
    def start_level(level_id: int) -> ActionReport:
        state = load_state()
        level = load_level(level_id)

        apply_level(level)

        state.current_level = level_id
        state.run_count = 0
        state.test_count = 0
        state.completed_objectives[level_id] = []
        state.fired_triggers[level_id] = []
        if level_id in state.completed_levels:
            state.completed_levels.remove(level_id)

        # Fire LEVEL_START narrative
        fired = set(state.fired_triggers.get(level_id, []))
        narratives, fired = narrative_engine.process(
            ["LEVEL_START"], level.narrative_triggers, level.narrative_script, fired,
        )
        state.fired_triggers[level_id] = list(fired)
        # Store narratives in state so the frontend can pick them up via /api/status
        state.pending_narratives = [n.model_dump() for n in narratives]
        save_state(state)

        report = ActionReport(narratives=narratives)
        report.objectives = GameEngine._show_objectives(level, state)
        return report

    @staticmethod
    def run() -> ActionReport:
        state = load_state()
        level = load_level(state.current_level)

        result = dbt_runner.run()
        state.run_count += 1

        events: list[str] = []
        rr = artifact_reader.read_run_results()
        if rr and rr.all_models_passed:
            events.append("RUN_SUCCESS")
        else:
            events.append("RUN_FAILURE")
        if state.run_count == 1:
            events.append("FIRST_RUN")

        # Check for hardcoded refs in mart files (only fire if they actually
        # wrote a schema.table pattern, not just because refs are missing)
        for obj in level.objectives:
            if obj.check.type == "no_hardcoded_refs":
                check_result = objective_checker.check(obj)
                if not check_result and check_result.reason and "hardcoded" in (check_result.reason or "").lower():
                    events.append("HARDCODE_DETECTED")

        report = ActionReport(
            dbt_output=result.stdout + result.stderr,
            dbt_success=result.success,
        )

        # Check objectives and detect newly completed
        report.objectives = GameEngine._check_all(level, state)
        report.newly_completed = GameEngine._update_completed(level, state, report.objectives)

        # Fire per-objective completion events for narrative triggers
        for obj_id in report.newly_completed:
            events.append(f"OBJECTIVE_{obj_id}_COMPLETE")

        # Check for level completion
        if GameEngine._all_complete(level, state):
            events.append("LEVEL_COMPLETE")
            report.level_complete = True
            report.xp_earned = level.xp_reward
            state.total_xp += level.xp_reward
            if level.id not in state.completed_levels:
                state.completed_levels.append(level.id)
            badge = EarnedBadge(
                id=level.badge.id, emoji=level.badge.emoji,
                name=level.badge.name, level_id=level.id,
            )
            state.earned_badges.append(badge)
            report.badge = badge

        # Fire narratives
        fired = set(state.fired_triggers.get(level.id, []))
        narratives, fired = narrative_engine.process(
            events, level.narrative_triggers, level.narrative_script, fired,
        )
        state.fired_triggers[level.id] = list(fired)
        state.pending_narratives = [n.model_dump() for n in narratives]
        report.narratives = narratives

        save_state(state)
        return report

    @staticmethod
    def test() -> ActionReport:
        state = load_state()
        level = load_level(state.current_level)

        result = dbt_runner.test()
        state.test_count += 1

        events: list[str] = []
        rr = artifact_reader.read_run_results()
        if rr and rr.has_test_failures:
            events.append("TEST_FAILURE")
        elif rr and rr.all_tests_passed:
            events.append("TEST_SUCCESS")

        report = ActionReport(
            dbt_output=result.stdout + result.stderr,
            dbt_success=result.success,
        )

        report.objectives = GameEngine._check_all(level, state)
        report.newly_completed = GameEngine._update_completed(level, state, report.objectives)

        for obj_id in report.newly_completed:
            events.append(f"OBJECTIVE_{obj_id}_COMPLETE")

        if GameEngine._all_complete(level, state):
            events.append("LEVEL_COMPLETE")
            report.level_complete = True
            report.xp_earned = level.xp_reward
            state.total_xp += level.xp_reward
            if level.id not in state.completed_levels:
                state.completed_levels.append(level.id)
            badge = EarnedBadge(
                id=level.badge.id, emoji=level.badge.emoji,
                name=level.badge.name, level_id=level.id,
            )
            state.earned_badges.append(badge)
            report.badge = badge

        fired = set(state.fired_triggers.get(level.id, []))
        narratives, fired = narrative_engine.process(
            events, level.narrative_triggers, level.narrative_script, fired,
        )
        state.fired_triggers[level.id] = list(fired)
        state.pending_narratives = [n.model_dump() for n in narratives]
        report.narratives = narratives

        save_state(state)
        return report

    @staticmethod
    def check_objectives() -> ActionReport:
        """Show objective state without re-evaluating (only run/test evaluate)."""
        state = load_state()
        level = load_level(state.current_level)
        report = ActionReport()
        report.objectives = GameEngine._show_objectives(level, state)
        return report

    @staticmethod
    def status() -> tuple[GameState, LevelConfig, list[tuple[ObjectiveDefinition, bool, str | None]]]:
        state = load_state()
        level = load_level(state.current_level)
        objectives = GameEngine._show_objectives(level, state)
        return state, level, objectives

    # ── Helpers ──────────────────────────────────────────────────────────

    @staticmethod
    def _show_objectives(
        level: LevelConfig, state: GameState,
    ) -> list[tuple[ObjectiveDefinition, bool, str | None]]:
        """Show objectives without evaluating — only previously completed ones show as passed."""
        completed = set(state.completed_objectives.get(level.id, []))
        return [
            (obj, obj.id in completed, None)
            for obj in level.objectives
        ]

    @staticmethod
    def _check_all(
        level: LevelConfig, state: GameState,
    ) -> list[tuple[ObjectiveDefinition, bool, str | None]]:
        completed = set(state.completed_objectives.get(level.id, []))
        results = []
        for obj in level.objectives:
            if obj.id in completed:
                results.append((obj, True, None))
            else:
                result = objective_checker.check(obj)
                results.append((obj, result.passed, result.reason))

        # "all_models_pass" should only complete when all other objectives are done
        # (prevents auto-passing on skeleton code that happens to compile)
        other_all_done = all(passed for obj, passed, _ in results if obj.check.type != "all_models_pass")
        for i, (obj, passed, reason) in enumerate(results):
            if obj.check.type == "all_models_pass" and passed and not other_all_done:
                results[i] = (obj, False, "Models compile, but complete the other objectives first, then run again.")

        return results

    @staticmethod
    def _update_completed(
        level: LevelConfig,
        state: GameState,
        checks: list[tuple[ObjectiveDefinition, bool, str | None]],
    ) -> list[str]:
        completed = set(state.completed_objectives.get(level.id, []))
        newly = []
        for obj, passed, _ in checks:
            if passed and obj.id not in completed:
                completed.add(obj.id)
                newly.append(obj.id)
        state.completed_objectives[level.id] = list(completed)
        return newly

    @staticmethod
    def _all_complete(level: LevelConfig, state: GameState) -> bool:
        completed = set(state.completed_objectives.get(level.id, []))
        return (
            len(level.objectives) > 0
            and all(obj.id in completed for obj in level.objectives)
            and level.id not in state.completed_levels
        )
