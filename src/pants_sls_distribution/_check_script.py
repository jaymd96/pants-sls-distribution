"""Pure Python check script generation (no Pants dependencies).

Generates service/monitoring/bin/check.sh for health checking.

Three modes (mutually exclusive):
  1. check_args: Palantir pattern - generates launcher-check.yml instead
     (handled by _launcher_config.CheckLauncherConfig). check.sh invokes
     the python-service-launcher in --check mode.
  2. check_command: Arbitrary command - generates check.sh that runs it.
  3. check_script: User-provided script - copied verbatim.
"""

from dataclasses import dataclass
from enum import Enum
from typing import Optional, Tuple


class CheckMode(str, Enum):
    """Health check mode."""

    CHECK_ARGS = "check_args"
    CHECK_COMMAND = "check_command"
    CHECK_SCRIPT = "check_script"
    NONE = "none"


@dataclass(frozen=True)
class CheckScriptResult:
    """Result of check script generation."""

    mode: CheckMode
    check_script_content: Optional[str] = None  # check.sh content (modes 1, 2)
    source_path: Optional[str] = None  # Original path for check_script mode


# Template for check_args mode: delegates to python-service-launcher --check
_CHECK_ARGS_SCRIPT = r"""#!/bin/bash
#
# Health check script for {service_name} (check_args mode).
# Delegates to python-service-launcher in --check mode, which reads
# service/bin/launcher-check.yml.

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${{BASH_SOURCE[0]}}")" && pwd)"
MONITORING_DIR="$(dirname "$SCRIPT_DIR")"
SERVICE_DIR="$(dirname "$MONITORING_DIR")"
DIST_ROOT="$(dirname "$SERVICE_DIR")"

# Detect platform and architecture
detect_launcher() {{
    local os arch
    os="$(uname -s | tr '[:upper:]' '[:lower:]')"
    arch="$(uname -m)"

    case "$arch" in
        x86_64|amd64) arch="amd64" ;;
        aarch64|arm64) arch="arm64" ;;
        *)
            echo "CRITICAL: Unsupported architecture: $arch" >&2
            exit 2
            ;;
    esac

    local launcher="${{DIST_ROOT}}/service/bin/${{os}}-${{arch}}/python-service-launcher"
    if [[ ! -x "$launcher" ]]; then
        echo "CRITICAL: Launcher binary not found: $launcher" >&2
        exit 2
    fi
    echo "$launcher"
}}

LAUNCHER="$(detect_launcher)"

cd "$DIST_ROOT"
exec "$LAUNCHER" --check --service-name "{service_name}"
"""

# Template for check_command mode: runs an arbitrary command
_CHECK_COMMAND_SCRIPT = r"""#!/bin/bash
#
# Health check script for {service_name} (check_command mode).
# Runs a custom health check command.

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${{BASH_SOURCE[0]}}")" && pwd)"
MONITORING_DIR="$(dirname "$SCRIPT_DIR")"
SERVICE_DIR="$(dirname "$MONITORING_DIR")"
DIST_ROOT="$(dirname "$SERVICE_DIR")"

cd "$DIST_ROOT"
exec {check_command}
"""


def generate_check_script(
    *,
    service_name: str,
    check_args: Optional[Tuple[str, ...]] = None,
    check_command: Optional[str] = None,
    check_script_path: Optional[str] = None,
) -> CheckScriptResult:
    """Generate the appropriate health check configuration.

    Exactly one of check_args, check_command, or check_script_path should be set,
    or none for no health checks.

    Args:
        service_name: Product name.
        check_args: Args for Palantir check_args pattern.
        check_command: Custom command string.
        check_script_path: Path to user-provided check.sh.

    Returns:
        CheckScriptResult with the generated content and mode.
    """
    set_count = sum(1 for v in [check_args, check_command, check_script_path] if v is not None)
    if set_count > 1:
        raise ValueError(
            "Only one of check_args, check_command, or check_script_path may be set."
        )

    if check_args is not None:
        # Mode 1: check_args - generate check.sh that invokes launcher --check
        # The launcher-check.yml is generated separately by _launcher_config
        content = _CHECK_ARGS_SCRIPT.format(
            service_name=service_name,
        ).lstrip("\n")
        return CheckScriptResult(
            mode=CheckMode.CHECK_ARGS,
            check_script_content=content,
        )

    if check_command is not None:
        # Mode 2: check_command - generate check.sh that runs the command
        content = _CHECK_COMMAND_SCRIPT.format(
            service_name=service_name,
            check_command=check_command,
        ).lstrip("\n")
        return CheckScriptResult(
            mode=CheckMode.CHECK_COMMAND,
            check_script_content=content,
        )

    if check_script_path is not None:
        # Mode 3: check_script - user provides the script, copy verbatim
        return CheckScriptResult(
            mode=CheckMode.CHECK_SCRIPT,
            source_path=check_script_path,
        )

    # No health check configured
    return CheckScriptResult(mode=CheckMode.NONE)
