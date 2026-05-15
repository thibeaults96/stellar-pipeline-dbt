# Stellar Pipeline

**Learn dbt by building a real data pipeline.** Powered by actual dbt + DuckDB, wrapped in a sci-fi narrative that follows the [official dbt Fundamentals course](https://learn.getdbt.com/courses/dbt-fundamentals).

You write real SQL. dbt actually compiles and runs it. Nothing is simulated.

![License](https://img.shields.io/badge/license-MIT-blue)

---

## What Is This?

Stellar Pipeline is an interactive training game for learning [dbt](https://www.getdbt.com/). You play the new analyst posted to Helios Waystation — a deep-space cargo hub where the previous data engineer rage-quit mid-shift and the warehouse is held together by one-off SQL scripts. Your job: rebuild the pipeline from scratch following the Analytics Development Lifecycle, with NAV (your pipeline companion AI), Commander Holt (your stakeholder), and Dr. Matsuri (the domain expert) walking you through it.

The nine core levels mirror the official **dbt Fundamentals** course flow, with environment and scheduling beats added to reflect how production dbt actually runs. Four bonus levels cover incremental models, snapshots, Jinja macros, and packages + variables.

Each level teaches a core dbt concept through hands-on objectives. You edit `.sql` and `.yml` files in a browser-based code editor, run real dbt commands, and get guided feedback from in-game characters as you progress.

**No prior dbt experience required.** Basic SQL knowledge (SELECT, FROM, WHERE, JOIN) is all you need.

## What You'll Learn

### Core arc — dbt Fundamentals

| Level | Title | Maps to | What You'll Build |
|-------|-------|---------|-------------------|
| 1 | Welcome to Helios | Welcome + Analytics Development Lifecycle | Project tour, `dbt seed`, first `dbt run` |
| 2 | Boot the Pipeline | Set Up dbt | Declare sources in YAML so dbt knows the raw tables |
| 3 | First Models | Models | Staging + marts, `source()`, `ref()`, joins, GROUP BY, inline materialization config (`{{ config(materialized='table') }}`) |
| 4 | The Source of Truth | Sources | `loaded_at_field`, freshness thresholds, `dbt source freshness` |
| 5 | Trust but Verify | Data Tests | `not_null`, `unique`, `accepted_values`, `relationships` |
| 6 | Tell the Story | Documentation | Model + column descriptions, doc blocks, `{{ doc('...') }}` |
| 7 | Ship It | Deployment (code side) | Full `dbt build` as the deploy command, simulated git promotion (commit → PR → merge), with deeper beats on branches / CI / code review |
| 8 | Set Up Production | Deployment (environment) | Configure a deployment environment — name, git branch, target schema, threads, pinned dbt version — mirroring how the dbt platform models environments |
| 9 | Schedule the Refresh | Orchestration | Define a job: pick the environment, type the dbt commands the job runs (`dbt build`, `dbt source freshness`), pick a schedule kind (Manual / Interval / Cron / On-merge), then trigger real runs |

### Bonus arc — Advanced concepts

| Level | Title | What You'll Build |
|-------|-------|-------------------|
| 10 | Refresh Crisis | Incremental models, `unique_key`, `is_incremental()` |
| 11 | Time Ledger | Snapshot models, `relation`, `timestamp`, `unique_key` |
| 12 | Priority Pipeline | Jinja macros — define a reusable `cargo_priority` macro and call it from a derived mart |
| 13 | Package Deal | `packages.yml` + `dbt deps`, dbt_utils integration (`generate_surrogate_key`), `vars:` block + `{{ var('name') }}` |

---

## Quick Start (GitHub Codespaces — no install)

From the repo page on GitHub, click **Code → Codespaces → Create codespace on main**. This runs on your own GitHub account, no local install needed.

Once it's ready, run:
```bash
./dev.sh
```
The game opens automatically at the forwarded port 3000.

---

## Local Setup

### Requirements

- **Node.js 18+** — [Download](https://nodejs.org/)
- **uv** (recommended) or **Python 3.10+**

Install uv (handles Python automatically):
```bash
curl -LsSf https://astral.sh/uv/install.sh | sh
```

### Install

```bash
git clone https://github.com/thibeaults96/stellar-pipeline.git
cd stellar-pipeline
bash setup.sh
```

If you have `uv`, setup handles everything (Python version, venv, deps). If not, it falls back to `pip` with your system Python.

### 3. Start the game

```bash
./dev.sh
```

This starts both the backend API server and the frontend dev server. You'll see:

```
  ━━━ STELLAR // PIPELINE ━━━

  Open http://localhost:3000
  Press Ctrl+C to stop.
```

Open **http://localhost:3000** in your browser.

### 4. Play

Click **BEGIN MISSION** to start Level 1. The game will guide you from there.

---

## How It Works

The game has three parts:

1. **A real dbt project** (`dbt_project/`) — this is where your SQL and YAML files live. When you edit code in the browser, it writes to these actual files on disk.

2. **A game engine** (`stellar_dbt/`) — checks your work against real dbt artifacts (`manifest.json`, `run_results.json`) and the DuckDB database. Tracks objectives, XP, and narrative progression.

3. **A web UI** (`frontend/`) — Monaco code editor, objective panel, terminal output, DAG visualization, and character dialogue. All running locally.

When you click "dbt run" in the game, it actually runs `dbt seed` + `dbt run` as a subprocess. The results are real. Errors are real dbt errors. The data is in a real DuckDB database file.

## Troubleshooting

### "Address already in use" when running `./dev.sh`

The script automatically kills processes on ports 8000 and 3000 before starting. If you still see this error, manually kill them:

```bash
lsof -ti:8000 | xargs kill -9
lsof -ti:3000 | xargs kill -9
```

Then run `./dev.sh` again.

### Frontend shows "Connecting to server..."

The backend isn't running. Make sure `./dev.sh` is running in a terminal. You should see both `[api]` and `[web]` lines in the output.

### dbt run fails with "Table not found"

This usually means the DuckDB database is stale from a previous level. Click the reset button (↺) in the top bar, or restart with `./dev.sh`.

### Monaco editor is blank or broken

Clear the Next.js cache and restart:

```bash
rm -rf frontend/.next
./dev.sh
```

---

## Contributing

Level definitions are YAML files in `stellar_dbt/levels/`. Each level defines:
- Objectives with check conditions
- Narrative triggers tied to objective completion
- Character dialogue
- Initial file templates and seed data

To add a new level, create `level_06.yml` following the pattern of existing levels, and add it to the `LEVELS` array in `frontend/components/StatusBar.tsx`.

## License

MIT
