#!/usr/bin/env bash
# Opens the Scalp City view in Firefox. Starts the dev server if it is not already up.
# Does not start the engine (run scripts/run_live.py yourself); the view connects to it at VITE_ENGINE_URL.
set -u
DIR="$(cd "$(dirname "$0")/.." && pwd)"
PORT="${SCALP_VIEW_PORT:-5174}"
ENGINE="${VITE_ENGINE_URL:-http://127.0.0.1:8010}"
LOG="${XDG_CACHE_HOME:-$HOME/.cache}/scalp-city-view.log"
up() { (exec 3<>"/dev/tcp/127.0.0.1/$PORT") 2>/dev/null; }
if ! up; then
  mkdir -p "$(dirname "$LOG")"
  (cd "$DIR" && VITE_ENGINE_URL="$ENGINE" nohup npx vite --port "$PORT" --strictPort >"$LOG" 2>&1 &)
  for _ in $(seq 1 40); do up && break; sleep 0.5; done
fi
exec firefox --new-window "http://localhost:$PORT/"
