"""Pure Python launcher config generation (no Pants dependencies).

Generates launcher-static.yml matching the Go StaticLauncherConfig struct
from python-service-launcher/launchlib/config.go.
"""

from dataclasses import dataclass, field
from typing import Any, Dict, Optional

import yaml


@dataclass(frozen=True)
class LauncherConfig:
    """Mirrors python-service-launcher's StaticLauncherConfig.

    YAML keys use camelCase to match the Go struct tags exactly.
    """

    # Required
    executable: str  # Path to PEX binary relative to dist root

    # Optional
    python_path: Optional[str] = None  # Path to Python interpreter
    entry_point: Optional[str] = None  # module:callable override
    args: tuple[str, ...] = ()
    env: dict[str, str] = field(default_factory=dict)
    python_opts: tuple[str, ...] = ()
    dirs: tuple[str, ...] = ("var/data/tmp", "var/log", "var/run")

    # Memory config
    memory_mode: str = "cgroup-aware"  # cgroup-aware, fixed, unmanaged
    memory_max_rss_percent: float = 75.0
    memory_heap_fragmentation_buffer: float = 0.10
    memory_malloc_trim_threshold: int = 131072
    memory_malloc_arena_max: int = 2

    # Resource limits
    max_open_files: int = 65536
    max_processes: int = 4096
    core_dump_enabled: bool = False

    # Watchdog
    watchdog_enabled: bool = True
    watchdog_poll_interval_seconds: int = 5
    watchdog_soft_limit_percent: float = 85.0
    watchdog_hard_limit_percent: float = 95.0
    watchdog_grace_period_seconds: int = 30

    def to_dict(self) -> dict[str, Any]:
        """Serialize to dict matching Go YAML tags."""
        config: dict[str, Any] = {
            "configType": "python",
            "configVersion": 1,
            "executable": self.executable,
        }

        if self.python_path:
            config["pythonPath"] = self.python_path
        if self.entry_point:
            config["entryPoint"] = self.entry_point
        if self.args:
            config["args"] = list(self.args)
        if self.env:
            config["env"] = dict(self.env)
        if self.python_opts:
            config["pythonOpts"] = list(self.python_opts)
        if self.dirs:
            config["dirs"] = list(self.dirs)

        # Memory config
        config["memory"] = {
            "mode": self.memory_mode,
            "maxRssPercent": self.memory_max_rss_percent,
            "heapFragmentationBuffer": self.memory_heap_fragmentation_buffer,
            "mallocTrimThreshold": self.memory_malloc_trim_threshold,
            "mallocArenaMax": self.memory_malloc_arena_max,
        }

        # Resource limits
        config["resources"] = {
            "maxOpenFiles": self.max_open_files,
            "maxProcesses": self.max_processes,
            "coreDumpEnabled": self.core_dump_enabled,
        }

        # Watchdog
        config["watchdog"] = {
            "enabled": self.watchdog_enabled,
            "pollIntervalSeconds": self.watchdog_poll_interval_seconds,
            "softLimitPercent": self.watchdog_soft_limit_percent,
            "hardLimitPercent": self.watchdog_hard_limit_percent,
            "gracePeriodSeconds": self.watchdog_grace_period_seconds,
        }

        return config

    def to_yaml(self) -> str:
        """Serialize to YAML string."""
        return yaml.dump(
            self.to_dict(),
            default_flow_style=False,
            sort_keys=False,
            allow_unicode=True,
        )


@dataclass(frozen=True)
class CheckLauncherConfig:
    """Launcher config for health check mode (launcher-check.yml).

    Used with check_args mode: same PEX binary, different arguments.
    """

    executable: str
    args: tuple[str, ...]
    entry_point: Optional[str] = None

    def to_dict(self) -> dict[str, Any]:
        config: dict[str, Any] = {
            "configType": "python",
            "configVersion": 1,
            "executable": self.executable,
        }
        if self.entry_point:
            config["entryPoint"] = self.entry_point
        config["args"] = list(self.args)
        return config

    def to_yaml(self) -> str:
        return yaml.dump(
            self.to_dict(),
            default_flow_style=False,
            sort_keys=False,
            allow_unicode=True,
        )


def build_launcher_config(
    *,
    service_name: str,
    executable: str,
    entry_point: Optional[str] = None,
    args: tuple[str, ...] = (),
    env: Optional[Dict[str, str]] = None,
    python_version: str = "3.11",
) -> LauncherConfig:
    """Build a LauncherConfig from sls_service target fields."""
    merged_env = {
        "PYTHONDONTWRITEBYTECODE": "1",
        "PYTHONUNBUFFERED": "1",
    }
    if env:
        merged_env.update(env)

    return LauncherConfig(
        executable=executable,
        entry_point=entry_point,
        args=args,
        env=merged_env,
    )


def build_check_launcher_config(
    *,
    executable: str,
    check_args: tuple[str, ...],
    entry_point: Optional[str] = None,
) -> CheckLauncherConfig:
    """Build a CheckLauncherConfig for the Palantir check_args pattern."""
    return CheckLauncherConfig(
        executable=executable,
        args=check_args,
        entry_point=entry_point,
    )
