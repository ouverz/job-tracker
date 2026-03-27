#!/bin/bash
set -e
DIR="$(cd "$(dirname "$0")" && pwd)"

echo "🚀 Starting Job Tracker..."

# ── Backend ────────────────────────────────────────────────────────────────────
cd "$DIR/backend"

# python-jobspy requires Python 3.10+; prefer 3.11 if available
PYTHON=$(which python3.11 2>/dev/null || which python3.12 2>/dev/null || which python3 2>/dev/null)
echo "Using Python: $($PYTHON --version)"

if [ ! -d ".venv" ]; then
  $PYTHON -m venv .venv
fi

source .venv/bin/activate
pip install -q --upgrade pip
pip install -q -r requirements.txt

uvicorn app.main:app --reload --port 8000 &
BACKEND_PID=$!

# ── Frontend ───────────────────────────────────────────────────────────────────
cd "$DIR/frontend"

if [ ! -d "node_modules" ]; then
  npm install --silent
fi

npm run dev &
FRONTEND_PID=$!

trap "kill $BACKEND_PID $FRONTEND_PID 2>/dev/null; exit" INT TERM

echo ""
echo "✅ Job Tracker running!"
echo "   App:      http://localhost:5173"
echo "   API docs: http://localhost:8000/docs"
echo ""
echo "Press Ctrl+C to stop."
wait
