"""Pure Python init.sh script generation (no Pants dependencies).

Generates the SLS init script (service/bin/init.sh) that delegates to
go-python-launcher for the current platform/architecture.

Based on go-python-launcher/scripts/init.sh.
"""

from __future__ import annotations

# The init.sh template uses bash with strict mode.
# It detects the platform/arch, locates the go-python-launcher binary,
# and supports start/stop/console/status/restart commands.

_INIT_SCRIPT_TEMPLATE = r"""#!/bin/bash
#
# SLS init script for {service_name}.
# Delegates to go-python-launcher for the current platform/architecture.
#
# Supports: start, stop, console, status, restart

set -euo pipefail

# --- Resolve paths ---
SCRIPT_DIR="$(cd "$(dirname "${{BASH_SOURCE[0]}}")" && pwd)"
SERVICE_DIR="$(dirname "$SCRIPT_DIR")"
DIST_ROOT="$(dirname "$SERVICE_DIR")"

# Detect platform and architecture for the correct go-python-launcher binary
detect_launcher() {{
    local os arch
    os="$(uname -s | tr '[:upper:]' '[:lower:]')"
    arch="$(uname -m)"

    case "$arch" in
        x86_64|amd64) arch="amd64" ;;
        aarch64|arm64) arch="arm64" ;;
        *)
            echo "Unsupported architecture: $arch" >&2
            exit 1
            ;;
    esac

    local launcher="${{SCRIPT_DIR}}/${{os}}-${{arch}}/go-python-launcher"
    if [[ ! -x "$launcher" ]]; then
        echo "Launcher binary not found or not executable: $launcher" >&2
        exit 1
    fi
    echo "$launcher"
}}

SERVICE_NAME="{service_name}"
LAUNCHER="$(detect_launcher)"
PID_FILE="${{DIST_ROOT}}/var/run/${{SERVICE_NAME}}.pid"

# --- Commands ---

do_start() {{
    if is_running; then
        echo "Service $SERVICE_NAME is already running (pid=$(cat "$PID_FILE"))"
        return 0
    fi

    echo "Starting $SERVICE_NAME..."

    # Ensure runtime directories exist
    mkdir -p "${{DIST_ROOT}}/var/log" "${{DIST_ROOT}}/var/run" "${{DIST_ROOT}}/var/data/tmp"

    local log_file="${{DIST_ROOT}}/var/log/${{SERVICE_NAME}}-startup.log"

    cd "$DIST_ROOT"
    nohup "$LAUNCHER" \
        --service-name "$SERVICE_NAME" \
        > "$log_file" 2>&1 &

    local pid=$!
    disown "$pid"
    echo "$pid" > "$PID_FILE"

    sleep 1
    if is_running; then
        echo "Started $SERVICE_NAME (pid=$pid)"
    else
        echo "Failed to start $SERVICE_NAME. Check $log_file for details." >&2
        return 1
    fi
}}

do_stop() {{
    if ! is_running; then
        echo "Service $SERVICE_NAME is not running"
        rm -f "$PID_FILE"
        return 0
    fi

    local pid
    pid="$(cat "$PID_FILE")"
    echo "Stopping $SERVICE_NAME (pid=$pid)..."

    kill -TERM "$pid" 2>/dev/null || true

    local waited=0
    while is_running && [[ $waited -lt {shutdown_timeout} ]]; do
        sleep 1
        waited=$((waited + 1))
    done

    if is_running; then
        echo "Graceful shutdown timed out after ${{waited}}s, sending SIGKILL"
        kill -KILL "$pid" 2>/dev/null || true
        sleep 1
    fi

    rm -f "$PID_FILE"
    echo "Stopped $SERVICE_NAME"
}}

do_console() {{
    if is_running; then
        echo "Service $SERVICE_NAME is already running (pid=$(cat "$PID_FILE"))" >&2
        return 1
    fi

    echo "Starting $SERVICE_NAME in console mode..."
    cd "$DIST_ROOT"
    exec "$LAUNCHER" --service-name "$SERVICE_NAME"
}}

do_status() {{
    if is_running; then
        local pid
        pid="$(cat "$PID_FILE")"
        echo "Service $SERVICE_NAME is running (pid=$pid)"
        return 0
    else
        echo "Service $SERVICE_NAME is not running"
        rm -f "$PID_FILE" 2>/dev/null
        return 1
    fi
}}

do_restart() {{
    do_stop
    do_start
}}

is_running() {{
    if [[ ! -f "$PID_FILE" ]]; then
        return 1
    fi

    local pid
    pid="$(cat "$PID_FILE")"

    if [[ -z "$pid" ]]; then
        return 1
    fi

    if kill -0 "$pid" 2>/dev/null; then
        return 0
    else
        return 1
    fi
}}

# --- Main ---

case "${{1:-}}" in
    start)   do_start ;;
    stop)    do_stop ;;
    console) do_console ;;
    status)  do_status ;;
    restart) do_restart ;;
    *)
        echo "Usage: $0 {{start|stop|console|status|restart}}" >&2
        exit 1
        ;;
esac
"""


def generate_init_script(
    *,
    service_name: str,
    shutdown_timeout: int = 30,
) -> str:
    """Generate init.sh content for an SLS distribution.

    Args:
        service_name: Product name (used for PID file, log file, display).
        shutdown_timeout: Seconds to wait for graceful shutdown before SIGKILL.

    Returns:
        Complete init.sh script content.
    """
    return _INIT_SCRIPT_TEMPLATE.format(
        service_name=service_name,
        shutdown_timeout=shutdown_timeout,
    ).lstrip("\n")
