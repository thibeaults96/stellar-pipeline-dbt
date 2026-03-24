#!/bin/bash
set -e

echo "━━━ STELLAR // PIPELINE — Codespaces Setup ━━━"

# Install uv
curl -LsSf https://astral.sh/uv/install.sh | sh
export PATH="$HOME/.local/bin:$PATH"

# Install Python dependencies
uv sync --quiet

# Install frontend dependencies
cd frontend && npm install --silent 2>/dev/null && cd ..

# Initialize game
uv run stellar start 1 >/dev/null 2>&1 || true

echo ""
echo "✅ Ready! Run ./dev.sh to start, then open the forwarded port 3000."
