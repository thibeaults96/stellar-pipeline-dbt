# Stellar Pipeline

**Learn dbt by building a real data pipeline.** Powered by actual dbt + DuckDB, wrapped in a sci-fi narrative.

You write real SQL. dbt actually compiles and runs it. Nothing is simulated.

![License](https://img.shields.io/badge/license-MIT-blue)

---

## What Is This?

Stellar Pipeline is an interactive training game for learning [dbt](https://www.getdbt.com/). You play as a new analyst at a space logistics company, building out a data pipeline while uncovering a mystery in the shipment data.

Each level teaches a core dbt concept through hands-on objectives. You edit `.sql` and `.yml` files in a browser-based code editor, run real dbt commands, and get guided feedback from AI characters as you progress.

**No prior dbt experience required.** Basic SQL knowledge (SELECT, FROM, WHERE, JOIN) is all you need.

## What You'll Learn

| Level | Title | What You'll Build |
|-------|-------|-------------------|
| 1 | First Day at the Federation | Staging models, `source()`, `ref()`, joins, GROUP BY |
| 2 | Something's Wrong with Kepler-7b | dbt tests (`not_null`, `unique`), source freshness |
| 3 | The Smuggler's Ledger | Model documentation, `accepted_values` tests |
| 4 | The Refresh Crisis | Incremental models, `unique_key`, `is_incremental()` |
| 5 | The Clean Handoff | CASE WHEN logic, investigation queries |

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
git clone https://github.com/yourusername/stellar-pipeline.git
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

### "Command not found: stellar"

If using uv, prefix with `uv run`:
```bash
uv run stellar start 1
```

If using pip, activate the venv:
```bash
source .venv/bin/activate
```

If that doesn't work, re-run setup:

```bash
bash setup.sh
```

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

## CLI Mode

If you prefer using your own code editor (VS Code, vim, etc.) instead of the browser UI:

```bash
uv run stellar start 1   # Start Level 1
# Edit files in dbt_project/models/ with your editor
uv run stellar run       # Run dbt and check objectives
uv run stellar test      # Run dbt tests
stellar status           # View progress and objectives
stellar hint             # Get hints for current objectives
stellar hint rename_columns  # Get hint for a specific objective
stellar reset            # Restart current level
stellar levels           # List all levels
```

The CLI and web UI use the same game engine and state file. You can switch between them.

---

## Project Structure

```
stellar-pipeline/
├── dbt_project/              # The actual dbt project (you edit files here)
│   ├── models/
│   │   ├── staging/          # Staging models (clean raw data)
│   │   ├── marts/            # Mart models (combine and transform)
│   │   └── sources/          # Source definitions (YAML)
│   ├── seeds/                # Source data (CSV files loaded into DuckDB)
│   ├── dbt_project.yml       # dbt project config
│   └── profiles.yml          # DuckDB connection config
│
├── frontend/                 # Web UI (Next.js + Tailwind + Monaco)
│   ├── app/                  # Page layout
│   ├── components/           # React components
│   └── hooks/                # API client
│
├── backend/                  # API server (FastAPI)
│   └── server.py             # All endpoints
│
├── stellar_dbt/              # Game engine
│   ├── cli.py                # CLI commands
│   ├── engine/               # Objective checking, narrative, state
│   ├── levels/               # Level definitions (YAML)
│   │   ├── level_01.yml
│   │   ├── level_02.yml
│   │   ├── level_03.yml
│   │   ├── level_04.yml
│   │   └── level_05.yml
│   └── ui/                   # CLI terminal rendering
│
├── setup.sh                  # One-time setup script
├── dev.sh                    # Start the game
├── pyproject.toml            # Python package config
└── LICENSE                   # MIT
```

## Contributing

Level definitions are YAML files in `stellar_dbt/levels/`. Each level defines:
- Objectives with check conditions
- Narrative triggers tied to objective completion
- Character dialogue
- Initial file templates and seed data

To add a new level, create `level_06.yml` following the pattern of existing levels, and add it to the `LEVELS` array in `frontend/components/StatusBar.tsx`.

## License

MIT
