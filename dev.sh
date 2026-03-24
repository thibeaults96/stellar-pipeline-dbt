#!/bin/bash
set -e

DIR="$(cd "$(dirname "$0")" && pwd)"
cd "$DIR"

# Ensure uv is on PATH (Codespaces installs to ~/.local/bin)
export PATH="$HOME/.local/bin:$PATH"

# Determine how to run Python commands
if command -v uv >/dev/null 2>&1; then
    PY="uv run"
elif [ -d ".venv" ]; then
    source .venv/bin/activate
    PY=""
else
    echo "Run 'bash setup.sh' first."
    exit 1
fi

# Kill any existing servers on our ports
lsof -ti:8000 | xargs kill -9 2>/dev/null || true
lsof -ti:3000 | xargs kill -9 2>/dev/null || true
sleep 1

# Start fresh
rm -f .stellar_state.json
rm -rf dbt_project/target dbt_project/logs dbt_project/stellar.duckdb
$PY stellar start 1 > /dev/null 2>&1 || true

echo ""
echo "  ━━━ STELLAR // PIPELINE ━━━"
echo ""
echo "  Open http://localhost:3000"
echo "  Press Ctrl+C to stop."
echo ""

# Run backend + frontend concurrently
cd frontend
npx concurrently \
  --names "api,web" \
  --prefix-colors "cyan,green" \
  --kill-others \
  "cd $DIR && $PY uvicorn backend.server:app --port 8000 --reload --log-level warning" \
  "next dev --port 3000"
