#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
RUNTIME_DIR="$ROOT_DIR/.runtime"
LOG_DIR="$ROOT_DIR/logs"

BACKEND_HOST="${BACKEND_HOST:-127.0.0.1}"
BACKEND_PORT="${BACKEND_PORT:-1100}"
FRONTEND_HOST="${FRONTEND_HOST:-127.0.0.1}"
FRONTEND_PORT="${FRONTEND_PORT:-1200}"
BACKEND_PATTERN="uvicorn main:app --host $BACKEND_HOST --port $BACKEND_PORT"
FRONTEND_PATTERN="http.server $FRONTEND_PORT --bind $FRONTEND_HOST"

mkdir -p "$RUNTIME_DIR" "$LOG_DIR"
export UV_LINK_MODE="${UV_LINK_MODE:-copy}"

is_running() {
    local pid_file="$1"
    local expected="$2"

    if [[ ! -f "$pid_file" ]]; then
        return 1
    fi

    local pid
    pid="$(cat "$pid_file")"

    if ! kill -0 "$pid" 2>/dev/null; then
        return 1
    fi

    local command
    command="$(ps -p "$pid" -o command= || true)"
    [[ "$command" == *"$expected"* ]]
}

find_pid() {
    pgrep -f "$1" | head -n 1
}

wait_for_pid() {
    local pattern="$1"
    local pid_file="$2"

    for _ in {1..50}; do
        local pid
        pid="$(find_pid "$pattern" || true)"
        if [[ -n "$pid" ]]; then
            echo "$pid" > "$pid_file"
            return
        fi
        sleep 0.2
    done

    echo "Failed to find running process matching: $pattern" >&2
    return 1
}

start_backend() {
    local pid_file="$RUNTIME_DIR/backend.pid"

    if is_running "$pid_file" "$BACKEND_PATTERN"; then
        echo "Backend already running on $BACKEND_HOST:$BACKEND_PORT (pid $(cat "$pid_file"))"
        return
    fi

    local existing_pid
    existing_pid="$(find_pid "$BACKEND_PATTERN" || true)"
    if [[ -n "$existing_pid" ]]; then
        echo "$existing_pid" > "$pid_file"
        echo "Backend already running on $BACKEND_HOST:$BACKEND_PORT (pid $existing_pid)"
        return
    fi

    echo "Syncing backend dependencies with uv..."
    (cd "$ROOT_DIR/backend" && uv sync)

    echo "Starting backend on $BACKEND_HOST:$BACKEND_PORT..."
    (
        cd "$ROOT_DIR/backend"
        nohup setsid uv run uvicorn main:app --host "$BACKEND_HOST" --port "$BACKEND_PORT" \
            > "$LOG_DIR/backend.log" 2>&1 &
    )
    wait_for_pid "$BACKEND_PATTERN" "$pid_file"
}

start_frontend() {
    local pid_file="$RUNTIME_DIR/frontend.pid"

    if is_running "$pid_file" "$FRONTEND_PATTERN"; then
        echo "Frontend already running on $FRONTEND_HOST:$FRONTEND_PORT (pid $(cat "$pid_file"))"
        return
    fi

    local existing_pid
    existing_pid="$(find_pid "$FRONTEND_PATTERN" || true)"
    if [[ -n "$existing_pid" ]]; then
        echo "$existing_pid" > "$pid_file"
        echo "Frontend already running on $FRONTEND_HOST:$FRONTEND_PORT (pid $existing_pid)"
        return
    fi

    echo "Starting frontend on $FRONTEND_HOST:$FRONTEND_PORT..."
    (
        cd "$ROOT_DIR/frontend"
        nohup setsid python3 -m http.server "$FRONTEND_PORT" --bind "$FRONTEND_HOST" \
            > "$LOG_DIR/frontend.log" 2>&1 &
    )
    wait_for_pid "$FRONTEND_PATTERN" "$pid_file"
}

start_backend
start_frontend

echo
echo "Local frontend: http://localhost:$FRONTEND_PORT"
echo "Remote frontend: https://oc.rustapp.uk:1201"
echo "Remote backend:  https://oc.rustapp.uk:1101"
echo "Logs: $LOG_DIR/backend.log and $LOG_DIR/frontend.log"
