# Git Level — Implementation Plan

A plan for the future Level 7 ("Deployment Protocol") that teaches the
feature-branch → dev → commit → CI → merge → prod lifecycle.

This plan supersedes the first attempt (reverted on 2026-05-04). The pedagogy
and engine integration patterns of that attempt were sound; the implementation
had a critical sandboxing flaw plus several correctness bugs in the objective
checks. This document captures both what to keep and what to fix.

---

## 1. Goals & non-goals

### Goals

- Teach the deployment lifecycle as six concrete steps: feature branch → dev
  run → commit → CI → merge → prod promotion.
- Reinforce *why* each step exists (each level narrative beat ties a step to a
  failure mode it prevents).
- Reuse the existing engine pattern: subprocess runner → game engine
  orchestrator → objective checker → narrative triggers → YAML level config.
- Operate safely in any environment without ever touching the user's real
  project repo.

### Non-goals

- Teaching git fundamentals (rebase, cherry-pick, conflict resolution). Those
  belong in a separate level if at all.
- Simulating a real remote, push, or PR review UI. CI is simulated locally;
  the narrative explains that in real life this would happen on push.
- Multi-developer collaboration scenarios. One player, one branch.

---

## 2. The critical fix: sandbox the git operations

The previous attempt set `cwd=PROJECT_ROOT` in `git_runner.py`, which meant
every `git checkout`, `commit`, `merge`, and the destructive `pre_setup_git()`
calls (`git checkout -B main`, `git branch -D feature/deployment-protocol`)
ran against the actual repo containing the game source. Playtesting added 15
commits to `main` and created a real `feature/deployment-protocol` branch. A
contributor with uncommitted work on `main` would lose it silently when
starting Level 7.

**The single non-negotiable design constraint for the rewrite: the game's git
operations must never touch the project repo.**

### Recommended approach: nested git inside `dbt_project/`

`apply_level()` already wipes `dbt_project/models/`, `macros/`, `snapshots/`,
and the DuckDB files on every level start. Treat `dbt_project/` as the
sandbox: initialize a fresh `.git/` inside it on Level 7 start, and run all
game-level git commands with `cwd=DBT_PROJECT_DIR`.

- The outer project repo's `.gitignore` adds `dbt_project/.git/` so the inner
  repo doesn't pollute the outer one.
- All player-edited files (models, macros, snapshots, schema YAML) already
  live inside `dbt_project/`, so the sandbox naturally contains everything
  the player can touch.
- `pre_setup_git()` becomes "nuke `.git/` and re-init" — fully idempotent and
  cannot affect the outer repo.

### Alternative considered: separate `.stellar_workspace/`

A separate copy-on-edit directory was considered and rejected. It breaks the
"you're editing real files" property that makes the rest of the game
pedagogically honest, requires bidirectional file sync, and adds a layer of
indirection between what the player sees and what dbt runs against.

### What `pre_setup_git` / `post_setup_git` do in the new design

```
pre_setup_git():
    rm -rf dbt_project/.git/
    cd dbt_project && git init -b main
    cd dbt_project && git config user.email "ae-7@stellar.local"
    cd dbt_project && git config user.name "AE-7"

post_setup_git():
    cd dbt_project && git add .
    cd dbt_project && git commit -m "[Stellar] Level 7: deployment baseline"
```

No `-B main`, no `-D` of any branch — there are no pre-existing branches in a
freshly-init'd repo. `level_07_reset` is now safe by construction.

### Levels 1–6 unaffected

`pre_setup_git` only runs when `level.git_enabled = True`. For all other
levels, `dbt_project/.git/` doesn't exist and the game behaves exactly as
today. The outer repo's gitignore entry costs nothing when the inner repo
isn't there.

---

## 3. Engine changes

### 3.1 `stellar_dbt/engine/git_runner.py` (new)

Same shape as the previous attempt, with these changes:

- All subprocess calls use `cwd=str(DBT_PROJECT_DIR)`, never `PROJECT_ROOT`.
- Promote `_run_git` to public (`run_git`) and call it from
  `objective_checker.py` instead of reaching into a private helper.
- Add public helpers used by the checker:
  - `commits_ahead_of(base: str) -> int`
  - `merges_since(sha: str | None, branch_substring: str) -> bool`
  - `working_tree_clean() -> bool`
  - `is_ancestor(a: str, b: str) -> bool` (for "is the feature branch's tip
    actually in main's history?")
- Drop the `--allow-empty` fallback in `commit()`. If there's nothing to
  commit, return a `GitResult` with `success=False` and a message the UI
  surfaces. The objective check should require real change, not a commit
  count.
- Fix `get_status()` porcelain parsing for renamed entries (`R  old -> new`).
- Capture and surface `git config user.email/user.name` errors clearly. On a
  fresh machine without global git config the first commit will fail with a
  cryptic message; the level-start config sets local identity to avoid this.

### 3.2 `stellar_dbt/engine/dbt_runner.py`

Thread `target` through every public function (as the previous attempt did)
with `target: str = "dev"` default. Verified: this is a no-op for levels 1–6
because `profiles.yml` already defaults to `target: dev`.

### 3.3 `stellar_dbt/engine/game_engine.py`

- Add `_finalize_action(level, state, report, events)` helper to dedupe the
  "evaluate objectives → check level completion → fire narratives → save
  state" tail that every action method needs. (Previous attempt got this
  right; keep it.)
- Add five action methods: `git_branch`, `git_commit`, `git_merge`, `ci_run`,
  `promote`.
- `promote()` must guard on being on `main`. If not, fail fast with a clear
  message and a `PROMOTION_BLOCKED` event. Currently the previous attempt let
  promotion run from any branch, which let the prod DB get populated from a
  feature branch and made the narrative ("we run dbt run, not dbt build")
  describe a flow that hadn't actually happened.
- `git_merge()` must refuse to merge if the working tree has uncommitted
  changes (`working_tree_clean() == False`). Fire a `GIT_MERGE_BLOCKED` event
  with a narrative explaining why ("commit or stash your work before merging
  — `git checkout main` would carry your uncommitted edits across branches").
- `ci_run()` reads `target/run_results.json` and only fires `CI_PASSED` if
  every model passed *and* every test passed (`all_tests_passed`, not just
  `all_models_passed`). The point of CI is to test, not just to build.

### 3.4 `stellar_dbt/engine/objective_checker.py`

Five new check types (`game_types.py` definitions in §4):

- **`git_on_branch`** — branch matches a glob (e.g. `feature/*`). Same as
  previous attempt.
- **`git_models_committed`** — there is at least one commit on the current
  branch ahead of `main`, AND the current branch's diff vs `main` includes
  changes to files under `models/`, `macros/`, or `snapshots/`. (Previous
  attempt only checked commit count, which was passable via empty commits.)
- **`git_branch_merged`** — there is a merge commit since the level baseline
  whose merged ref name matches the level's branch *pattern* (not a
  hardcoded string). Use `is_ancestor(feature_tip, main)` as a stronger signal
  than parsing merge commit messages.
- **`ci_passed`** — read `target/run_results.json` from the CI database run,
  not just check that `stellar_ci.duckdb` exists. The previous attempt's
  "table exists in CI DB" check would tick green for a partial dbt build that
  errored mid-run. The right signal is `all_models_passed and
  all_tests_passed` against the CI artifacts.
- **`promotion_succeeded`** — `target/run_results.json` shows all models
  passed against the prod target, AND the prod DuckDB has the expected models
  (parameterized via the check definition, not hardcoded).

Other cleanup:

- Move all imports to top of file. Previous attempt scattered
  `from stellar_dbt.engine import git_runner` inside individual check
  branches.
- Parameterize expected model names. The check should accept
  `expected_models: list[str]` rather than hardcoding `{"fct_voss_investigation",
  "fct_trade_routes", "stg_shipments"}`, so future levels can reuse `ci_passed`
  and `promotion_succeeded`.

### 3.5 `stellar_dbt/levels/loader.py`

- On `apply_level`, also delete `dbt_project/.git/` if `git_enabled=True`.
  This is what makes level reset safe and idempotent.
- Delete `stellar_ci.duckdb` and `stellar_prod.duckdb` on every level start
  (previous attempt got this right).

### 3.6 `stellar_dbt/config.py`

Add `PROD_DB_PATH` and `CI_DB_PATH` (previous attempt had this — keep).

---

## 4. Schema changes (`stellar_dbt/models/game_types.py`)

Add five new Pydantic check types in the discriminated union. Mirror the
previous attempt's structure but with parameterization fixed:

```python
class GitOnBranch(BaseModel):
    type: Literal["git_on_branch"] = "git_on_branch"
    pattern: str  # glob, e.g. "feature/*"

class GitModelsCommitted(BaseModel):
    type: Literal["git_models_committed"] = "git_models_committed"
    paths: list[str] = ["models/", "macros/", "snapshots/"]  # configurable

class GitBranchMerged(BaseModel):
    type: Literal["git_branch_merged"] = "git_branch_merged"
    branch_pattern: str = "feature/*"  # not a hardcoded literal
    into: str = "main"

class CiPassed(BaseModel):
    type: Literal["ci_passed"] = "ci_passed"
    expected_models: list[str]  # required, no default

class PromotionSucceeded(BaseModel):
    type: Literal["promotion_succeeded"] = "promotion_succeeded"
    expected_models: list[str]
```

Add to `LevelConfig`:

```python
git_enabled: bool = False
```

Add to `GameState`:

```python
git_baseline_sha: str | None = None
```

---

## 5. Level YAML (`stellar_dbt/levels/level_07.yml`)

The narrative arc and objectives from the previous attempt are good — keep
them with these tweaks:

- `git_branch_merged` references `branch_pattern: "feature/*"` instead of the
  literal `feature/deployment-protocol`. The branch input field stays
  editable, but any `feature/*` name now satisfies the level. (If we want to
  keep a default for the input, that's a frontend concern.)
- `ci_passed` and `promotion_succeeded` declare their `expected_models`
  inline so the checker stays generic.
- Add a `nt_merge_blocked` and `nt_promote_blocked` narrative trigger for the
  new guard events from §3.3.
- Consider adding an explicit "fail CI on purpose" beat: pre-seed the level
  with one model that has a failing test, force the player to run CI, see it
  fail, fix the model, commit, re-run CI, and *then* merge. This is the most
  pedagogically valuable moment in the level and the current draft skips
  past it. Optional — could be Level 7b.

---

## 6. Backend (`backend/server.py`)

Mirror the previous attempt's endpoints — they're correctly shaped:

- `GET /api/git/status` → branch, dirty flag, file lists
- `POST /api/git/branch` `{name}`
- `POST /api/git/commit` `{message}`
- `POST /api/git/merge` `{branch}`
- `POST /api/ci/run`
- `POST /api/promote`

All return `ActionReport` (so they participate in objective evaluation and
narrative firing) except `/api/git/status` which returns the raw status
dict.

---

## 7. Frontend

### 7.1 `frontend/components/GitPanel.tsx`

Keep the previous attempt's layout — it's good UX. Add:

- An "uncommitted" warning state on the merge button when `gitStatus.dirty`
  is true. Tooltip: "commit your changes first — merging with a dirty working
  tree carries them across branches."
- A small badge near the branch indicator showing commits-ahead-of-main
  count (helps players see that their commit registered).
- Disable `promote → prod` when `branch !== "main"`. The button is currently
  always enabled and just fails server-side.

### 7.2 `frontend/components/GameShell.tsx`

Keep the previous attempt's wiring. Two improvements:

- Lift the `level.id >= 7` check into a `level.gitEnabled` flag exposed via
  `/api/status` so the frontend doesn't hardcode level numbers (which
  becomes wrong the moment Level 8 is added).
- Refresh git status after every action that could change it, not just git
  actions — `dbt run` doesn't change git state, but a level reset does.

### 7.3 `frontend/hooks/useGameApi.ts`

`GitStatus` type + five new methods. Previous attempt got this right.

---

## 8. Edge cases & failure modes to handle

Each of these should have a deterministic, narrative-aware outcome rather
than crashing or silently passing:

1. **Player commits with no changes.** New `commit()` returns failure; UI
   shows "nothing to commit" in the terminal panel; no CI is triggered;
   objective stays incomplete.
2. **Player runs CI before committing.** CI runs against the *current
   working tree* (since dbt reads files from disk), but the merge gate
   should still require a commit. Distinct objectives: `ci_passed` and
   `commit_working_models` are independent.
3. **Player merges with uncommitted changes.** Blocked by §3.3 guard. Fires
   `GIT_MERGE_BLOCKED`.
4. **Player promotes before merging.** Blocked by §3.3 guard. Fires
   `PROMOTION_BLOCKED`.
5. **Player resets level mid-flow.** `apply_level` wipes `.git/` and
   `stellar_ci.duckdb` and `stellar_prod.duckdb`; new baseline commit is made;
   game state's `git_baseline_sha` is updated. No carryover from the previous
   attempt.
6. **Player creates a branch with a bad name (spaces, conflicts).** Surface
   git's actual error in the terminal panel. Don't pre-validate — the
   error message is part of what the level teaches.
7. **CI fails because a test fails.** `CI_FAILED` event fires; narrative
   guidance points to the terminal output; objective stays incomplete; player
   fixes the model, commits the fix, re-runs CI. This is the level working
   as intended and should feel good, not like a bug.
8. **Fresh machine has no `git config user.name`.** §3.1 sets local identity
   on level start so the first commit succeeds without depending on global
   config.
9. **Player has a stale `dbt_project/.git/` from a previous level 7
   attempt.** `pre_setup_git` rm -rf's it. No leakage.

---

## 9. Testing strategy

- **Unit tests for `git_runner.py`**: each public function tested against a
  `tmp_path` git repo. Verify `cwd` is honored, identity is set, error paths
  return `GitResult(success=False, ...)`.
- **Unit tests for the new objective checks**: each check type with a fixture
  repo in known states (clean, dirty, on-branch, merged, etc.).
- **Integration test for the full level 7 flow**: scripted, end-to-end —
  start level, create branch, edit a file, commit, run CI, merge, promote,
  assert level complete + badge awarded. Run this in CI to catch regressions
  to the surrounding engine.
- **Manual smoke test that levels 1–6 still pass** after the
  `dbt_runner.target` parameter change.
- **Manual verification that the outer repo is untouched** after a level 7
  playthrough. `git status` of the outer repo should be exactly the same
  before and after starting, playing, and resetting Level 7. This is the
  acceptance test for the sandboxing fix.

---

## 10. Phased rollout

Implementing this in one PR risks regression in levels 1–6. Suggested phases:

1. **Phase 1 — sandboxing infrastructure.** Add `git_runner.py` operating on
   a configurable `cwd`. Add the outer `.gitignore` entry for
   `dbt_project/.git/`. No level uses it yet. Land alone. Manual test: outer
   repo stays clean across multiple levels of dbt project mutation.
2. **Phase 2 — dbt target threading.** Thread `target` through `dbt_runner`
   with `target="dev"` default. Add CI/prod profiles. No level uses non-dev.
   Land alone. Verify levels 1–6 unchanged.
3. **Phase 3 — engine + checker.** Add the five game actions, the five
   objective check types, and the schema additions. Add a hidden `level_99`
   test fixture that exercises all of them. No production level uses it yet.
4. **Phase 4 — frontend GitPanel + level 7 YAML.** Wire up the UI and ship
   the level. This is the only phase visible to players.
5. **Phase 5 (optional) — the "CI catches a real bug" beat.** Pre-seed a
   failing test, force the player through fix-recommit-rerun. Either part of
   level 7 or a level 7b.

---

## 11. Open questions to resolve before starting

- Do we want the player to type the branch name (current design) or pick from
  a dropdown? Typing teaches the convention; dropdown is harder to softlock.
  Lean: typing, with `feature/*` validation client-side and the level
  accepting any `feature/*` name server-side.
- Should the merge step include a simulated PR review (modal asking
  "approve?" before the merge button activates), or is the narrative line
  "in a real team, an approving reviewer plus a green CI check are typically
  required" enough? Lean: narrative is enough for now. Adding a real review
  step is its own design problem.
- Should "promote" run `dbt build` against prod (testing twice) or `dbt run`
  (current design, trusting CI)? Current design matches industry practice.
  Worth a sentence in the narrative explaining why we *don't* test in prod.
- Where does VOSS fit? The previous attempt's epilogue tied off the VOSS
  storyline in level 7, but level 6 already does that. Level 7's
  ADMIRAL-7 narrator works — keep it as a coda about deployment discipline,
  not a continuation of the smuggling investigation.

---

## 12. What to keep from the previous attempt verbatim

- The `_finalize_action` helper in `game_engine.py`.
- The narrative arc in `level_07.yml` (the six steps, the ADMIRAL-7 voice,
  the protocol explanation, the "every step exists because someone skipped
  it" framing).
- The `GitPanel.tsx` layout (branch indicator, three input rows, four
  action buttons, amber CI button, accent promote button).
- The CI / prod profile additions in `profiles.yml`.
- The `GitStatus` interface and `postJson` helper in `useGameApi.ts`.

## 13. What to discard

- Anything in `git_runner.py` that uses `PROJECT_ROOT` as `cwd`.
- The `pre_setup_git` calls to `git checkout -B main` and
  `git branch -D feature/deployment-protocol`.
- The `--allow-empty` fallback in `commit()`.
- The "table exists" approximation in `ci_passed` and `promotion_succeeded`.
- The hardcoded model name set in `objective_checker.py`.
- The hardcoded `feature/deployment-protocol` literal in the merge
  objective.
- The unrelated level 6 narrative tweak — if we still want it, it goes in
  its own commit.
