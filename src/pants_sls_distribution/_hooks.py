"""Pure Python hook init system integration (no Pants dependencies).

Provides embedded shell scripts and validation for the POSIX hook
lifecycle system (entrypoint.sh + hooks.sh).

Hook phases:
    pre-configure -> configure -> pre-startup -> startup ->
    post-startup  -> [READY]   -> (wait)      ->
    pre-shutdown  -> shutdown   -> [EXIT]
"""

import re

HOOK_PHASES = (
    "pre-configure",
    "configure",
    "pre-startup",
    "startup",
    "post-startup",
    "pre-shutdown",
    "shutdown",
)

_HOOK_PATH_RE = re.compile(
    r"^(?P<phase>[a-z-]+)\.d/(?P<name>[a-zA-Z0-9_.-]+\.sh)$"
)


def get_entrypoint_script() -> str:
    """Return the embedded entrypoint.sh content.

    Adapted from the hook init system so SERVICE_ROOT auto-detects
    the distribution root from the ``service/bin/`` location.
    """
    return '''\
#!/bin/sh
# entrypoint.sh — Container lifecycle entrypoint (POSIX sh compatible)
#
# Lifecycle:
#   pre-configure.d → configure.d → pre-startup.d → startup.d →
#   post-startup.d  → [READY]     → (wait)        →
#   pre-shutdown.d  → shutdown.d  → [EXIT]

set -eu

# ---------------------------------------------------------------------------
# Resolve paths — auto-detect dist root from service/bin/ location
# ---------------------------------------------------------------------------
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
SERVICE_ROOT="${SERVICE_ROOT:-$(cd "$SCRIPT_DIR/../.." && pwd)}"

# Source the hook library
. "${SERVICE_ROOT}/service/lib/hooks.sh"

# ---------------------------------------------------------------------------
# Directories
# ---------------------------------------------------------------------------
HOOK_BASE="${SERVICE_ROOT}/hooks"
HOOK_LOG_DIR="${SERVICE_ROOT}/var/logs"
HOOK_METRIC_DIR="${SERVICE_ROOT}/var/metrics"
HOOK_STATE_DIR="${SERVICE_ROOT}/var/state"

export SERVICE_ROOT HOOK_BASE HOOK_LOG_DIR HOOK_METRIC_DIR HOOK_STATE_DIR

# Service mode — allows same image to behave differently
SERVICE_MODE="${SERVICE_MODE:-default}"
export SERVICE_MODE

# PID tracking
MAIN_PID=""
SHUTDOWN_IN_PROGRESS=""

# ---------------------------------------------------------------------------
# Signal handling
# ---------------------------------------------------------------------------
_shutdown() {
    if [ -n "$SHUTDOWN_IN_PROGRESS" ]; then
        return
    fi
    SHUTDOWN_IN_PROGRESS=1

    _log "Shutdown signal received"

    # Pre-shutdown hooks (warn mode — best effort)
    run_hooks_warn "${HOOK_BASE}/pre-shutdown.d" \\
        "${HOOK_LOG_DIR}/pre-shutdown.log"

    # Kill main process if running
    if [ -n "$MAIN_PID" ] && kill -0 "$MAIN_PID" 2>/dev/null; then
        _log "Sending TERM to main process (PID $MAIN_PID)"
        kill -TERM "$MAIN_PID" 2>/dev/null || true

        # Grace period
        _grace="${SHUTDOWN_GRACE_SECONDS:-10}"
        _waited=0
        while kill -0 "$MAIN_PID" 2>/dev/null && [ "$_waited" -lt "$_grace" ]; do
            sleep 1
            _waited=$(( _waited + 1 ))
        done

        # Force kill if still alive
        if kill -0 "$MAIN_PID" 2>/dev/null; then
            _log_err "Main process did not exit after ${_grace}s, sending KILL"
            kill -KILL "$MAIN_PID" 2>/dev/null || true
        fi
    fi

    # Shutdown hooks
    run_hooks_warn "${HOOK_BASE}/shutdown.d" \\
        "${HOOK_LOG_DIR}/shutdown.log"

    # Clean state
    rm -f "${HOOK_STATE_DIR}/initialized"
    rm -f "${HOOK_STATE_DIR}/main.pid"

    _log "Shutdown complete"
    exit 0
}

trap _shutdown TERM INT

# ---------------------------------------------------------------------------
# Bootstrap
# ---------------------------------------------------------------------------
_ensure_dirs
mkdir -p "${HOOK_BASE}" 2>/dev/null || true

_log "=== Service starting (mode=${SERVICE_MODE}) ==="

# ---------------------------------------------------------------------------
# Phase 1: Pre-configure
# ---------------------------------------------------------------------------
_log "--- Phase: pre-configure ---"
run_hooks_timed "${HOOK_BASE}/pre-configure.d" \\
    "${HOOK_LOG_DIR}/pre-configure.log" || {
    _log_err "Pre-configure failed, aborting"
    exit 1
}

# ---------------------------------------------------------------------------
# Phase 2: Configure
# ---------------------------------------------------------------------------
_log "--- Phase: configure ---"

_env_file="${SERVICE_ROOT}/var/environment.sh"
if [ -f "$_env_file" ]; then
    _log "Sourcing environment from sidecar: $_env_file"
    . "$_env_file"
fi

run_hooks_timed "${HOOK_BASE}/configure.d" \\
    "${HOOK_LOG_DIR}/configure.log" || {
    _log_err "Configure failed, aborting"
    exit 1
}

# ---------------------------------------------------------------------------
# Phase 3: Pre-startup
# ---------------------------------------------------------------------------
_log "--- Phase: pre-startup ---"
run_hooks_timed "${HOOK_BASE}/pre-startup.d" \\
    "${HOOK_LOG_DIR}/pre-startup.log" || {
    _log_err "Pre-startup failed, aborting"
    exit 1
}

# ---------------------------------------------------------------------------
# Phase 4: Startup
# ---------------------------------------------------------------------------
_log "--- Phase: startup ---"
run_hooks_timed "${HOOK_BASE}/startup.d" \\
    "${HOOK_LOG_DIR}/startup.log" || {
    _log_err "Startup failed, aborting"
    exit 1
}

# Pick up PID if the hook wrote one
if [ -f "${HOOK_STATE_DIR}/main.pid" ]; then
    MAIN_PID="$(cat "${HOOK_STATE_DIR}/main.pid")"
    _log "Main process PID: $MAIN_PID"
fi

# ---------------------------------------------------------------------------
# Phase 5: Post-startup
# ---------------------------------------------------------------------------
_log "--- Phase: post-startup ---"
run_hooks_timed "${HOOK_BASE}/post-startup.d" \\
    "${HOOK_LOG_DIR}/post-startup.log" || {
    _log_err "Post-startup failed (service may be degraded)"
    # Don\'t abort — main process is already running
}

# ---------------------------------------------------------------------------
# Ready
# ---------------------------------------------------------------------------
touch "${HOOK_STATE_DIR}/initialized"
_log "=== Service ready ==="

# ---------------------------------------------------------------------------
# Wait
# ---------------------------------------------------------------------------
if [ -n "$MAIN_PID" ] && kill -0 "$MAIN_PID" 2>/dev/null; then
    _log "Waiting on main process (PID $MAIN_PID)"
    wait "$MAIN_PID" 2>/dev/null || true
    _log "Main process exited"
    _shutdown
else
    _log "No main process — waiting for signal"
    while true; do
        sleep 60 &
        wait $! 2>/dev/null || true
    done
fi
'''


def get_hooks_library() -> str:
    """Return the embedded hooks.sh library content."""
    return '''\
#!/bin/sh
# hooks.sh — Core hook execution library (POSIX sh compatible)
#
# Provides:
#   run_hooks       <dir> [logfile]   — run all scripts in dir, halt on failure
#   run_hooks_timed <dir> [logfile]   — same, but emit timing metrics
#   run_hooks_warn  <dir> [logfile]   — run all, log failures but continue

HOOK_BASE="${HOOK_BASE:-/opt/service}"
HOOK_LOG_DIR="${HOOK_LOG_DIR:-/var/run/service/logs}"
HOOK_METRIC_DIR="${HOOK_METRIC_DIR:-/var/run/service/metrics}"
HOOK_STATE_DIR="${HOOK_STATE_DIR:-/var/run/service/state}"

_log() {
    printf '[%s] [hooks] %s\\n' "$(date -u '+%Y-%m-%dT%H:%M:%SZ')" "$*"
}

_log_err() {
    _log "ERROR: $*" >&2
}

_millis() {
    if date '+%s%N' >/dev/null 2>&1; then
        echo $(( $(date '+%s%N') / 1000000 ))
    else
        echo $(( $(date '+%s') * 1000 ))
    fi
}

_ensure_dirs() {
    mkdir -p "$HOOK_LOG_DIR" "$HOOK_METRIC_DIR" "$HOOK_STATE_DIR" 2>/dev/null || true
}

run_hooks() {
    _dir="$1"
    _logfile="${2:-/dev/null}"

    if [ ! -d "$_dir" ]; then
        _log "No hook directory: $_dir (skipping)"
        return 0
    fi

    _count=0
    for _script in "$_dir"/*.sh; do
        [ -f "$_script" ] || continue
        [ -x "$_script" ] || continue
        _count=$(( _count + 1 ))

        _name="$(basename "$_script")"
        _log "Running hook: $_name"

        _rc=0
        "$_script" >> "$_logfile" 2>&1 || _rc=$?
        if [ "$_rc" -ne 0 ]; then
            _log_err "Hook failed: $_name (exit $_rc)"
            return "$_rc"
        fi
    done

    if [ "$_count" -eq 0 ]; then
        _log "No hooks in $_dir"
    else
        _log "Completed $_count hook(s) from $_dir"
    fi

    return 0
}

run_hooks_timed() {
    _dir="$1"
    _logfile="${2:-/dev/null}"
    _phase="$(basename "$_dir" | sed 's/\\.d$//')"

    _ensure_dirs

    if [ ! -d "$_dir" ]; then
        _log "No hook directory: $_dir (skipping)"
        return 0
    fi

    _phase_start="$(_millis)"
    _hook_timings=""
    _count=0
    _failed=""

    for _script in "$_dir"/*.sh; do
        [ -f "$_script" ] || continue
        [ -x "$_script" ] || continue
        _count=$(( _count + 1 ))

        _name="$(basename "$_script")"
        _log "Running hook: $_name"

        _hook_start="$(_millis)"

        _hook_rc=0
        "$_script" >> "$_logfile" 2>&1 || _hook_rc=$?

        _hook_end="$(_millis)"
        _hook_ms=$(( _hook_end - _hook_start ))

        [ -n "$_hook_timings" ] && _hook_timings="${_hook_timings},"
        _hook_timings="${_hook_timings}{\\"hook\\":\\"${_name}\\",\\"ms\\":${_hook_ms},\\"rc\\":${_hook_rc}}"

        if [ "$_hook_rc" -ne 0 ]; then
            _log_err "Hook failed: $_name (exit $_hook_rc, ${_hook_ms}ms)"
            _failed="$_name"
            break
        fi

        _log "Hook complete: $_name (${_hook_ms}ms)"
    done

    _phase_end="$(_millis)"
    _phase_ms=$(( _phase_end - _phase_start ))

    if [ -n "$_failed" ]; then
        _status="failed"
    else
        _status="ok"
    fi

    printf '{"phase":"%s","status":"%s","total_ms":%d,"hooks":[%s]}\\n' \\
        "$_phase" "$_status" "$_phase_ms" "$_hook_timings" \\
        > "${HOOK_METRIC_DIR}/${_phase}.json"

    if [ -n "$_failed" ]; then
        return 1
    fi

    _log "Phase $_phase complete: $_count hook(s) in ${_phase_ms}ms"
    return 0
}

run_hooks_warn() {
    _dir="$1"
    _logfile="${2:-/dev/null}"

    if [ ! -d "$_dir" ]; then
        _log "No hook directory: $_dir (skipping)"
        return 0
    fi

    _count=0
    _failures=0

    for _script in "$_dir"/*.sh; do
        [ -f "$_script" ] || continue
        [ -x "$_script" ] || continue
        _count=$(( _count + 1 ))

        _name="$(basename "$_script")"
        _log "Running hook: $_name"

        _rc=0
        "$_script" >> "$_logfile" 2>&1 || _rc=$?
        if [ "$_rc" -ne 0 ]; then
            _log_err "Hook failed (continuing): $_name (exit $_rc)"
            _failures=$(( _failures + 1 ))
        fi
    done

    if [ "$_failures" -gt 0 ]; then
        _log "Completed with $_failures failure(s) out of $_count hook(s)"
    fi

    return 0
}
'''


def generate_startup_script(service_name: str) -> str:
    """Generate the startup.d/00-main.sh script.

    Starts the python-service-launcher in the background and writes PID.
    """
    return f'''\
#!/bin/sh
# Auto-generated: Start python-service-launcher for {service_name}
set -eu

os="$(uname -s | tr '[:upper:]' '[:lower:]')"
arch="$(uname -m)"
case "$arch" in x86_64|amd64) arch="amd64" ;; aarch64|arm64) arch="arm64" ;; esac

LAUNCHER="${{SERVICE_ROOT}}/service/bin/${{os}}-${{arch}}/python-service-launcher"
"$LAUNCHER" --service-name "{service_name}" &
echo $! > "${{HOOK_STATE_DIR}}/main.pid"
'''


def validate_hook_paths(hooks: dict[str, str]) -> None:
    """Validate that hook keys match ``<phase>.d/<name>.sh`` pattern.

    Args:
        hooks: Mapping of hook paths to source file paths.

    Raises:
        ValueError: If any key has an invalid format or unknown phase.
    """
    for key in hooks:
        match = _HOOK_PATH_RE.match(key)
        if not match:
            raise ValueError(
                f"Invalid hook path '{key}': must match '<phase>.d/<name>.sh' "
                f"(e.g., 'pre-startup.d/10-migrate.sh')"
            )
        phase = match.group("phase")
        if phase not in HOOK_PHASES:
            raise ValueError(
                f"Unknown hook phase '{phase}' in '{key}'. "
                f"Valid phases: {', '.join(HOOK_PHASES)}"
            )
