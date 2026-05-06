#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
RUNTIME_DIR="$ROOT_DIR/.runtime"

BACKEND_HOST="${BACKEND_HOST:-127.0.0.1}"
BACKEND_PORT="${BACKEND_PORT:-1100}"
FRONTEND_HOST="${FRONTEND_HOST:-127.0.0.1}"
FRONTEND_PORT="${FRONTEND_PORT:-1200}"
BACKEND_PATTERN="uvicorn main:app --host $BACKEND_HOST --port $BACKEND_PORT"
FRONTEND_PATTERN="http.server $FRONTEND_PORT --bind $FRONTEND_HOST"

find_pid() {
    pgrep -f "$1" | head -n 1
}

stop_service() {
    local name="$1"
    local expected="$2"
    local pid_file="$RUNTIME_DIR/$name.pid"
    local pid=""

    if [[ -f "$pid_file" ]]; then
        pid="$(cat "$pid_file")"
    fi

    if [[ -z "$pid" ]] || ! kill -0 "$pid" 2>/dev/null; then
        pid="$(find_pid "$expected" || true)"
    fi

    if [[ -z "$pid" ]]; then
        echo "$name is not running"
        rm -f "$pid_file"
        return
    fi

    local command
    command="$(ps -p "$pid" -o command= || true)"
    if [[ "$command" != *"$expected"* ]]; then
        echo "Refusing to stop $name: pid $pid does not look like $expected"
        echo "Command: $command"
        return 1
    fi

    echo "Stopping $name (pid $pid)..."
    local pgid
    pgid="$(ps -p "$pid" -o pgid= | tr -d ' ')"

    if [[ -n "$pgid" ]]; then
        kill -- "-$pgid" 2>/dev/null || kill "$pid"
    else
        kill "$pid"
    fi

    for _ in {1..50}; do
        if [[ -z "$(find_pid "$expected" || true)" ]]; then
            rm -f "$pid_file"
            echo "$name stopped"
            return
        fi
        sleep 0.2
    done

    echo "$name did not stop after 10 seconds; leaving pid file at $pid_file"
    return 1
}

stop_service "frontend" "$FRONTEND_PATTERN"
stop_service "backend" "$BACKEND_PATTERN"
