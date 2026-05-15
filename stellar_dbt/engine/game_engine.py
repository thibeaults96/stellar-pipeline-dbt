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


def _run_dbt_command(raw: str):
    """Parse a player-typed dbt command and dispatch to the runner.
    Used by the scheduled-job command runner. Returns the dbt_runner.DbtResult
    or a synthetic failure DbtResult if the command isn't recognized.
    Whitespace-tolerant: 'dbt   build  ' → 'dbt build'.

    Supports node selection: 'dbt run --select <selector>' (also --select=X
    and short -s) is parsed and the selector is passed straight through to
    dbt. Selectors can be model names, paths (staging.+), or tags (tag:nightly)."""
    cleaned = " ".join(raw.strip().split()).lower()
    tokens = cleaned.split()

    # ── Selector form: dbt <subcmd> --select <selector> ──
    if len(tokens) >= 4 and tokens[0] == "dbt" and tokens[1] in {"run", "build", "test", "seed"}:
        flag, rest = tokens[2], tokens[3:]
        selector: str | None = None
        if flag in {"--select", "-s"} and rest:
            selector = rest[0]
        elif flag.startswith("--select="):
            selector = flag.split("=", 1)[1]
        elif flag.startswith("-s="):
            selector = flag.split("=", 1)[1]
        if selector:
            subcmd = tokens[1]
            # Seeds inherit the seed runner's pre-step, but for run/build/test
            # the selector form skips the implicit seed — selection implies
            # the player knows what they're targeting.
            from stellar_dbt.engine.dbt_runner import _run_dbt
            return _run_dbt(subcmd, "--select", selector)

    # ── Whole-project commands ──
    dispatch = {
        "dbt seed": dbt_runner.seed,
        "dbt run": dbt_runner.run,
        "dbt test": dbt_runner.test,
        "dbt build": dbt_runner.build,
        "dbt deps": dbt_runner.deps,
        "dbt snapshot": dbt_runner.snapshot,
        "dbt compile": dbt_runner.compile_project,
        "dbt source freshness": dbt_runner.source_freshness,
    }
    fn = dispatch.get(cleaned)
    if fn is None:
        return dbt_runner.DbtResult(
            success=False,
            stdout="",
            stderr=(
                f"Unknown command: `{raw}`\n"
                "Recognized: dbt seed / dbt deps / dbt run / dbt test / dbt build / "
                "dbt snapshot / dbt compile / dbt source freshness\n"
                "Also: dbt run|build|test --select <model_or_tag>"
            ),
            return_code=2,
        )
    return fn()


class GameEngine:

    @staticmethod
    def start_level(level_id: int) -> ActionReport:
        state = load_state()
        level = load_level(level_id)

        apply_level(level)

        state.current_level = level_id
        state.run_count = 0
        state.test_count = 0
        if level_id not in state.completed_levels:
            # Fresh or in-progress level — clear progress so the player can
            # work the objectives without stale state interfering.
            state.completed_objectives[level_id] = []
            state.fired_triggers[level_id] = []
        # If the level is already in completed_levels we deliberately keep
        # completed_objectives and fired_triggers so navigating back to a
        # finished level keeps it green and doesn't require redoing work.
        # /api/reset removes the level from completed_levels before calling
        # start_level, so reset still produces a clean wipe.

        # Fire LEVEL_START narrative
        fired = set(state.fired_triggers.get(level_id, []))
        completed = set(state.completed_objectives.get(level_id, []))
        narratives, fired = narrative_engine.process(
            ["LEVEL_START"], level.narrative_triggers, level.narrative_script, fired, completed,
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
        dbt_passed = bool(rr and rr.all_models_passed)
        if not dbt_passed:
            events.append("RUN_FAILURE")
        # FIRST_RUN only fires on a successful first run. Levels hook this
        # event to introduce post-build observations ("models built — now look
        # at the data"), which read as gaslighting if dbt actually errored.
        if state.run_count == 1 and dbt_passed:
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

        # Gate RUN_SUCCESS on actual progress: a successful dbt build with the
        # placeholder template still passes, and we don't want congratulatory
        # narratives ("Models compiled, looking good") to fire when the
        # player hasn't met any objectives yet.
        any_complete = any(ok for _, ok, _ in report.objectives)
        if dbt_passed and any_complete:
            events.append("RUN_SUCCESS")

        # Fire per-objective completion events for narrative triggers
        for obj_id in report.newly_completed:
            events.append(f"OBJECTIVE_{obj_id}_COMPLETE")

        # Check for level completion
        GameEngine._maybe_award_level_complete(level, state, events, report)

        # Fire narratives
        fired = set(state.fired_triggers.get(level.id, []))
        completed = set(state.completed_objectives.get(level.id, []))
        narratives, fired = narrative_engine.process(
            events, level.narrative_triggers, level.narrative_script, fired, completed,
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

        GameEngine._maybe_award_level_complete(level, state, events, report)

        fired = set(state.fired_triggers.get(level.id, []))
        completed = set(state.completed_objectives.get(level.id, []))
        narratives, fired = narrative_engine.process(
            events, level.narrative_triggers, level.narrative_script, fired, completed,
        )
        state.fired_triggers[level.id] = list(fired)
        state.pending_narratives = [n.model_dump() for n in narratives]
        report.narratives = narratives

        save_state(state)
        return report

    @staticmethod
    def build() -> ActionReport:
        """Run dbt build (seed + run + test in dependency order)."""
        state = load_state()
        level = load_level(state.current_level)

        result = dbt_runner.build()
        state.run_count += 1
        state.test_count += 1

        events: list[str] = []
        rr = artifact_reader.read_run_results()
        dbt_passed = bool(rr and rr.all_models_passed)
        if not dbt_passed:
            events.append("RUN_FAILURE")
        if rr and rr.has_test_failures:
            events.append("TEST_FAILURE")
        elif rr and rr.all_tests_passed:
            events.append("TEST_SUCCESS")
        # See run() for why FIRST_RUN is gated on dbt success.
        if state.run_count == 1 and dbt_passed:
            events.append("FIRST_RUN")

        for obj in level.objectives:
            if obj.check.type == "no_hardcoded_refs":
                check_result = objective_checker.check(obj)
                if not check_result and check_result.reason and "hardcoded" in (check_result.reason or "").lower():
                    events.append("HARDCODE_DETECTED")

        report = ActionReport(
            dbt_output=result.stdout + result.stderr,
            dbt_success=result.success,
        )

        report.objectives = GameEngine._check_all(level, state)
        report.newly_completed = GameEngine._update_completed(level, state, report.objectives)

        # See run() for why RUN_SUCCESS is gated on actual objective progress.
        any_complete = any(ok for _, ok, _ in report.objectives)
        if dbt_passed and any_complete:
            events.append("RUN_SUCCESS")

        for obj_id in report.newly_completed:
            events.append(f"OBJECTIVE_{obj_id}_COMPLETE")

        GameEngine._maybe_award_level_complete(level, state, events, report)

        fired = set(state.fired_triggers.get(level.id, []))
        completed = set(state.completed_objectives.get(level.id, []))
        narratives, fired = narrative_engine.process(
            events, level.narrative_triggers, level.narrative_script, fired, completed,
        )
        state.fired_triggers[level.id] = list(fired)
        state.pending_narratives = [n.model_dump() for n in narratives]
        report.narratives = narratives

        save_state(state)
        return report

    @staticmethod
    def snapshot() -> ActionReport:
        """Run dbt snapshot."""
        state = load_state()
        level = load_level(state.current_level)

        result = dbt_runner.snapshot()

        events: list[str] = []
        events.append("SNAPSHOT_RUN")

        report = ActionReport(
            dbt_output=result.stdout + result.stderr,
            dbt_success=result.success,
        )

        report.objectives = GameEngine._check_all(level, state)
        report.newly_completed = GameEngine._update_completed(level, state, report.objectives)

        for obj_id in report.newly_completed:
            events.append(f"OBJECTIVE_{obj_id}_COMPLETE")

        GameEngine._maybe_award_level_complete(level, state, events, report)

        fired = set(state.fired_triggers.get(level.id, []))
        completed = set(state.completed_objectives.get(level.id, []))
        narratives, fired = narrative_engine.process(
            events, level.narrative_triggers, level.narrative_script, fired, completed,
        )
        state.fired_triggers[level.id] = list(fired)
        state.pending_narratives = [n.model_dump() for n in narratives]
        report.narratives = narratives

        save_state(state)
        return report

    @staticmethod
    def seed() -> ActionReport:
        """Run `dbt seed` — load CSVs from seeds/ into the warehouse.
        First command a player runs on a new project, hence its own button."""
        state = load_state()
        level = load_level(state.current_level)

        result = dbt_runner.seed()

        events: list[str] = ["SEED_RUN"]
        if result.success:
            events.append("SEED_SUCCESS")
        else:
            events.append("SEED_FAILURE")

        report = ActionReport(
            dbt_output=result.stdout + result.stderr,
            dbt_success=result.success,
        )

        report.objectives = GameEngine._check_all(level, state)
        report.newly_completed = GameEngine._update_completed(level, state, report.objectives)

        for obj_id in report.newly_completed:
            events.append(f"OBJECTIVE_{obj_id}_COMPLETE")

        GameEngine._maybe_award_level_complete(level, state, events, report)

        fired = set(state.fired_triggers.get(level.id, []))
        completed = set(state.completed_objectives.get(level.id, []))
        narratives, fired = narrative_engine.process(
            events, level.narrative_triggers, level.narrative_script, fired, completed,
        )
        state.fired_triggers[level.id] = list(fired)
        state.pending_narratives = [n.model_dump() for n in narratives]
        report.narratives = narratives

        save_state(state)
        return report

    @staticmethod
    def deps() -> ActionReport:
        """Run `dbt deps` — install packages declared in packages.yml.
        Same structural shape as seed/freshness/snapshot."""
        state = load_state()
        level = load_level(state.current_level)

        result = dbt_runner.deps()

        events: list[str] = ["DEPS_RUN"]
        if result.success:
            events.append("DEPS_SUCCESS")
        else:
            events.append("DEPS_FAILURE")

        report = ActionReport(
            dbt_output=result.stdout + result.stderr,
            dbt_success=result.success,
        )

        report.objectives = GameEngine._check_all(level, state)
        report.newly_completed = GameEngine._update_completed(level, state, report.objectives)

        for obj_id in report.newly_completed:
            events.append(f"OBJECTIVE_{obj_id}_COMPLETE")

        GameEngine._maybe_award_level_complete(level, state, events, report)

        fired = set(state.fired_triggers.get(level.id, []))
        completed = set(state.completed_objectives.get(level.id, []))
        narratives, fired = narrative_engine.process(
            events, level.narrative_triggers, level.narrative_script, fired, completed,
        )
        state.fired_triggers[level.id] = list(fired)
        state.pending_narratives = [n.model_dump() for n in narratives]
        report.narratives = narratives

        save_state(state)
        return report

    @staticmethod
    def freshness() -> ActionReport:
        """Run `dbt source freshness`. Best teaching tool for this — if the
        player's freshness config is wrong, dbt itself will say why."""
        state = load_state()
        level = load_level(state.current_level)

        result = dbt_runner.source_freshness()

        events: list[str] = ["FRESHNESS_RUN"]
        if result.success:
            events.append("FRESHNESS_SUCCESS")
        else:
            events.append("FRESHNESS_FAILURE")

        report = ActionReport(
            dbt_output=result.stdout + result.stderr,
            dbt_success=result.success,
        )

        report.objectives = GameEngine._check_all(level, state)
        report.newly_completed = GameEngine._update_completed(level, state, report.objectives)

        for obj_id in report.newly_completed:
            events.append(f"OBJECTIVE_{obj_id}_COMPLETE")

        GameEngine._maybe_award_level_complete(level, state, events, report)

        fired = set(state.fired_triggers.get(level.id, []))
        completed = set(state.completed_objectives.get(level.id, []))
        narratives, fired = narrative_engine.process(
            events, level.narrative_triggers, level.narrative_script, fired, completed,
        )
        state.fired_triggers[level.id] = list(fired)
        state.pending_narratives = [n.model_dump() for n in narratives]
        report.narratives = narratives

        save_state(state)
        return report

    @staticmethod
    def _state_action(events: list[str], mutator) -> ActionReport:
        """Apply a pure state mutation, then run the standard objective/event
        pipeline. Used by the Deploy and Schedule levels where 'actions' are
        UI interactions instead of dbt subprocess calls."""
        state = load_state()
        level = load_level(state.current_level)
        mutator(state)
        # Persist immediately — objective checkers read state from disk to
        # evaluate git_state / schedule_state checks, so this mutation has to
        # be visible to them before _check_all runs.
        save_state(state)

        report = ActionReport()
        report.objectives = GameEngine._check_all(level, state)
        report.newly_completed = GameEngine._update_completed(level, state, report.objectives)

        for obj_id in report.newly_completed:
            events.append(f"OBJECTIVE_{obj_id}_COMPLETE")

        GameEngine._maybe_award_level_complete(level, state, events, report)

        fired = set(state.fired_triggers.get(level.id, []))
        completed = set(state.completed_objectives.get(level.id, []))
        narratives, fired = narrative_engine.process(
            events, level.narrative_triggers, level.narrative_script, fired, completed,
        )
        state.fired_triggers[level.id] = list(fired)
        state.pending_narratives = [n.model_dump() for n in narratives]
        report.narratives = narratives

        save_state(state)
        return report

    @staticmethod
    def git_stage() -> ActionReport:
        def m(state):
            state.git.staged = True
        return GameEngine._state_action(["GIT_STAGE"], m)

    @staticmethod
    def git_commit(message: str) -> ActionReport:
        def m(state):
            state.git.staged = True
            state.git.committed = True
            state.git.commit_message = message
        return GameEngine._state_action(["GIT_COMMIT"], m)

    @staticmethod
    def git_open_pr() -> ActionReport:
        def m(state):
            state.git.pr_opened = True
            # CI passes if the player's most recent dbt build/run succeeded —
            # use run_results.json as the proxy. In the absence of one we still
            # mark CI green so the level is completable on a fresh start; the
            # narrative explains the dependency.
            rr = artifact_reader.read_run_results()
            state.git.ci_passing = bool(rr is None or rr.all_models_passed)
        return GameEngine._state_action(["GIT_PR_OPENED"], m)

    @staticmethod
    def git_merge() -> ActionReport:
        def m(state):
            state.git.merged = True
        return GameEngine._state_action(["GIT_MERGED"], m)

    @staticmethod
    def schedule_set(
        kind: str | None = None,
        expression: str | None = None,
        commands: list[str] | None = None,
        environment_name: str | None = None,
    ) -> ActionReport:
        """Mutate one or more fields on the scheduled-job definition.
        `None` for any field means "leave unchanged" so the UI can patch
        individual fields without round-tripping the whole object.

        Each section fires its own event so narrative triggers can listen
        for the specific change they care about — saving the environment
        shouldn't fire the kind-picker narrative, etc."""
        def m(state):
            if kind is not None:
                state.schedule.kind = kind
            if expression is not None:
                state.schedule.expression = expression
            if commands is not None:
                # Drop blank lines from the editor; keep order, dedupe whitespace
                state.schedule.commands = [" ".join(c.split()) for c in commands if c.strip()]
            if environment_name is not None:
                state.schedule.environment_name = environment_name

        events: list[str] = ["SCHEDULE_SET"]
        if kind is not None:
            events.append("SCHEDULE_KIND_SET")
        if commands is not None:
            events.append("SCHEDULE_COMMANDS_SET")
        if environment_name is not None:
            events.append("SCHEDULE_ENV_SET")
        return GameEngine._state_action(events, m)

    @staticmethod
    def env_set(
        name: str | None = None,
        git_branch: str | None = None,
        target_schema: str | None = None,
        threads: int | None = None,
        dbt_version: str | None = None,
    ) -> ActionReport:
        """Patch one or more EnvironmentState fields. Like schedule_set,
        None means leave unchanged so the UI can update piecemeal."""
        def m(state):
            if name is not None:
                state.environment.name = name
            if git_branch is not None:
                state.environment.git_branch = git_branch
            if target_schema is not None:
                state.environment.target_schema = target_schema
            if threads is not None:
                state.environment.threads = threads
            if dbt_version is not None:
                state.environment.dbt_version = dbt_version
        return GameEngine._state_action(["ENVIRONMENT_SET"], m)

    @staticmethod
    def schedule_trigger() -> ActionReport:
        """Simulate a scheduled run. Parses the player's command list and
        dispatches each command through dbt_runner. If the list is empty,
        defaults to a single `dbt build` so newcomers see something useful."""
        state = load_state()
        level = load_level(state.current_level)
        cmds = state.schedule.commands or ["dbt build"]

        outputs: list[str] = []
        success = True
        for cmd in cmds:
            outputs.append(f"\n$ {cmd}\n")
            result = _run_dbt_command(cmd)
            outputs.append(result.stdout + result.stderr)
            if not result.success:
                success = False
                outputs.append(f"\n[command failed — stopping the job]\n")
                break

        events: list[str] = ["SCHEDULE_TRIGGERED"]
        events.append("SCHEDULE_RUN_SUCCESS" if success else "SCHEDULE_RUN_FAILURE")

        joined = "".join(outputs)
        state = load_state()
        state.schedule.run_count += 1
        state.schedule.last_run_output = joined[-2000:]  # cap for storage
        save_state(state)

        def m(_state):
            pass

        report = GameEngine._state_action(events, m)
        report.dbt_output = joined
        report.dbt_success = success
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

        # "all_models_pass" should only complete once the editor work is done,
        # so skeleton code that happens to compile doesn't auto-pass it. But
        # don't gate on action-only objectives (dbt test / dbt snapshot) —
        # those represent separate user actions and the player completes them
        # *after* a successful dbt run. If we gated on those, all_green would
        # flip back to False after a snapshot run wipes run_results.json of
        # model entries, and the player would have to dbt run a second time.
        action_only_types = {"tests_ran_with_failures", "snapshot_ran"}
        other_all_done = all(
            passed
            for obj, passed, _ in results
            if obj.check.type != "all_models_pass"
            and obj.check.type not in action_only_types
        )
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

    @staticmethod
    def _maybe_award_level_complete(
        level: LevelConfig,
        state: GameState,
        events: list[str],
        report: ActionReport,
    ) -> None:
        """If every objective on this level is done, fire LEVEL_COMPLETE,
        award XP, badge, and mark the level completed. No-op otherwise.
        Mutates state, events, and report in place. Called from every action
        method to keep the completion logic in one place."""
        if not GameEngine._all_complete(level, state):
            return
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
