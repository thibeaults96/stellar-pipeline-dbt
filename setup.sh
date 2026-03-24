#!/bin/bash
set -e

echo ""
echo "  ━━━ STELLAR // PIPELINE ━━━"
echo "  Learn dbt"
echo ""

# Check for uv (preferred) or fall back to pip
if command -v uv >/dev/null 2>&1; then
    echo "Installing Python dependencies (uv)..."
    uv sync --quiet
else
    echo "  'uv' not found. Install it for the fastest setup:"
    echo "    curl -LsSf https://astral.sh/uv/install.sh | sh"
    echo ""
    echo "  Falling back to pip..."

    command -v python3 >/dev/null 2>&1 || { echo "Error: python3 is required."; exit 1; }
    python3 -c "import sys; assert sys.version_info >= (3, 10)" 2>/dev/null || {
        echo "Error: Python 3.10+ required."; python3 --version; exit 1
    }

    if [ ! -d ".venv" ]; then
        python3 -m venv .venv
    fi
    source .venv/bin/activate
    pip install -e . --quiet 2>&1 | tail -1
fi

# Frontend
command -v node >/dev/null 2>&1 || { echo "Error: Node.js 18+ is required. Install from https://nodejs.org"; exit 1; }
echo "Installing frontend dependencies..."
cd frontend && npm install --silent 2>/dev/null && cd ..

# Initialize game
echo "Initializing Level 1..."
if command -v uv >/dev/null 2>&1; then
    uv run stellar start 1 >/dev/null 2>&1 || true
else
    source .venv/bin/activate
    stellar start 1 >/dev/null 2>&1 || true
fi

echo ""
echo "  ✅ Setup complete!"
echo ""
echo "  To play, run:"
echo ""
echo "    ./dev.sh"
echo ""
echo "  Then open http://localhost:3000"
echo ""
