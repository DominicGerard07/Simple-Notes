
#!/usr/bin/env bash
set -e

# Change directory to the script's folder
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

echo "============================================"
echo "📝 Starting Flask SimpleNotes Application"
echo "============================================"

# Check for Python 3
if ! command -v python3 &> /dev/null; then
    echo "❌ Error: Python 3 is required but not installed."
    exit 1
fi

# Set up virtual environment if not present
if [ ! -d ".venv" ]; then
    echo "📦 Creating virtual environment (.venv)..."
    python3 -m venv .venv
    echo "⬇️ Installing requirements..."
    .venv/bin/pip install -q --upgrade pip
    .venv/bin/pip install -q -r requirements.txt
else
    # Ensure dependencies are satisfied
    if ! .venv/bin/python3 -c "import flask" &> /dev/null; then
        echo "⬇️ Installing requirements into existing virtualenv..."
        .venv/bin/pip install -q -r requirements.txt
    fi
fi

# Seed sample notes if database doesn't exist yet
if [ ! -f "notes.db" ]; then
    echo "🌱 Seeding initial sample notes..."
    .venv/bin/python3 sample_notes.py
fi

PORT="${PORT:-5000}"
echo ""
echo "🚀 Application is ready!"
echo "👉 Open your browser at: http://127.0.0.1:${PORT}"
echo "Press Ctrl+C to stop the server."
echo "============================================"
echo ""

exec .venv/bin/python3 app.py
