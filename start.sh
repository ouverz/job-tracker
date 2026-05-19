#!/bin/bash
set -e
DIR="$(cd "$(dirname "$0")" && pwd)"

# Usage: ./start.sh [--dev]
#   default  — production mode: builds frontend, serves everything from port 8000 (Tailscale-friendly)
#   --dev    — dev mode: hot-reload Vite on :5173 + backend on :8000 (local only)
DEV=0
[[ "${1}" == "--dev" ]] && DEV=1

echo "🚀 Starting Job Tracker..."

# ── Backend ────────────────────────────────────────────────────────────────────
cd "$DIR/backend"

PYTHON=$(which python3.11 2>/dev/null || which python3.12 2>/dev/null || which python3 2>/dev/null || which python3.13 2>/dev/null)
if [ -z "$PYTHON" ]; then
  echo "❌ Python 3.11+ not found. Install it from https://python.org" && exit 1
fi
if ! $PYTHON -c "import sys; assert sys.version_info >= (3,11), 'need 3.11+'" 2>/dev/null; then
  echo "❌ Python 3.11+ required (found $($PYTHON --version 2>&1))" && exit 1
fi
echo "Using Python: $($PYTHON --version)"

if [ ! -d ".venv" ]; then
  $PYTHON -m venv .venv
fi

source .venv/bin/activate
pip install -q --upgrade pip
pip install -q -r requirements.txt

# ── Frontend ───────────────────────────────────────────────────────────────────
cd "$DIR/frontend"

if [ ! -d "node_modules" ]; then
  npm install --silent
fi

if [ "$DEV" -eq 1 ]; then
  # Dev mode: hot-reload, local only
  cd "$DIR/backend"
  uvicorn app.main:app --reload --port 8000 &
  BACKEND_PID=$!

  cd "$DIR/frontend"
  npm run dev &
  FRONTEND_PID=$!

  trap "kill $BACKEND_PID $FRONTEND_PID 2>/dev/null; exit" INT TERM

  echo ""
  echo "✅ Job Tracker running (dev mode)"
  echo "   App:      http://localhost:5173"
  echo "   API docs: http://localhost:8000/docs"
  echo ""
  echo "Press Ctrl+C to stop."
  wait
else
  # Production mode: build frontend, serve everything from port 8000 on all interfaces
  echo "Building frontend..."
  npm run build --silent

  cd "$DIR/backend"
  uvicorn app.main:app --host 0.0.0.0 --port 8000 &
  BACKEND_PID=$!

  trap "kill $BACKEND_PID 2>/dev/null; exit" INT TERM

  # Cross-platform local IP detection (macOS: ipconfig, Linux: hostname -I)
  LOCAL_IP=$(ipconfig getifaddr en0 2>/dev/null \
    || ipconfig getifaddr en1 2>/dev/null \
    || hostname -I 2>/dev/null | awk '{print $1}' \
    || echo "127.0.0.1")

  echo ""
  echo "✅ Job Tracker running (production mode)"
  echo "   Local:     http://localhost:8000"
  echo "   Network:   http://${LOCAL_IP}:8000"
  echo "   Tailscale: use your Tailscale IP on port 8000"
  echo "   API docs:  http://localhost:8000/docs"
  echo ""
  echo "Press Ctrl+C to stop."
  wait
fi
