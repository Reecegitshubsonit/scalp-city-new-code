#!/usr/bin/env bash
# Stops the view's dev server (not the engine).
PORT="${SCALP_VIEW_PORT:-5174}"
pids=$(ss -ltnp 2>/dev/null | grep ":$PORT " | grep -o 'pid=[0-9]*' | cut -d= -f2 | sort -u)
[ -n "$pids" ] && kill $pids
