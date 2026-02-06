"""Tests for launcher config generation (pure functions, no Pants engine)."""

from __future__ import annotations

import yaml
import pytest

from pants_sls_distribution._launcher_config import (
    CheckLauncherConfig,
    LauncherConfig,
    build_check_launcher_config,
    build_launcher_config,
)


class TestLauncherConfig:
    """Test LauncherConfig dataclass and serialization."""

    def test_minimal_config(self):
        config = LauncherConfig(executable="service/bin/app.pex")
        d = config.to_dict()
        assert d["configType"] == "python"
        assert d["configVersion"] == 1
        assert d["executable"] == "service/bin/app.pex"

    def test_full_config(self):
        config = LauncherConfig(
            executable="service/bin/app.pex",
            python_path="/usr/bin/python3",
            entry_point="app:main",
            args=("--host", "0.0.0.0"),
            env={"FOO": "bar"},
            python_opts=("-u",),
            dirs=("var/data/tmp", "var/log"),
        )
        d = config.to_dict()
        assert d["pythonPath"] == "/usr/bin/python3"
        assert d["entryPoint"] == "app:main"
        assert d["args"] == ["--host", "0.0.0.0"]
        assert d["env"] == {"FOO": "bar"}
        assert d["pythonOpts"] == ["-u"]
        assert d["dirs"] == ["var/data/tmp", "var/log"]

    def test_memory_config_defaults(self):
        config = LauncherConfig(executable="app.pex")
        d = config.to_dict()
        mem = d["memory"]
        assert mem["mode"] == "cgroup-aware"
        assert mem["maxRssPercent"] == 75.0
        assert mem["heapFragmentationBuffer"] == 0.10
        assert mem["mallocTrimThreshold"] == 131072
        assert mem["mallocArenaMax"] == 2

    def test_resource_config_defaults(self):
        config = LauncherConfig(executable="app.pex")
        d = config.to_dict()
        res = d["resources"]
        assert res["maxOpenFiles"] == 65536
        assert res["maxProcesses"] == 4096
        assert res["coreDumpEnabled"] is False

    def test_watchdog_config_defaults(self):
        config = LauncherConfig(executable="app.pex")
        d = config.to_dict()
        wd = d["watchdog"]
        assert wd["enabled"] is True
        assert wd["pollIntervalSeconds"] == 5
        assert wd["softLimitPercent"] == 85.0
        assert wd["hardLimitPercent"] == 95.0
        assert wd["gracePeriodSeconds"] == 30

    def test_custom_memory_mode(self):
        config = LauncherConfig(
            executable="app.pex",
            memory_mode="fixed",
            memory_max_rss_percent=90.0,
        )
        d = config.to_dict()
        assert d["memory"]["mode"] == "fixed"
        assert d["memory"]["maxRssPercent"] == 90.0

    def test_watchdog_disabled(self):
        config = LauncherConfig(executable="app.pex", watchdog_enabled=False)
        d = config.to_dict()
        assert d["watchdog"]["enabled"] is False

    def test_to_yaml_roundtrip(self):
        config = LauncherConfig(
            executable="service/bin/my-service.pex",
            entry_point="app:main",
            args=("--port", "8080"),
            env={"ENV": "prod"},
        )
        yaml_str = config.to_yaml()
        parsed = yaml.safe_load(yaml_str)
        assert parsed["configType"] == "python"
        assert parsed["configVersion"] == 1
        assert parsed["executable"] == "service/bin/my-service.pex"
        assert parsed["entryPoint"] == "app:main"
        assert parsed["args"] == ["--port", "8080"]
        assert parsed["env"]["ENV"] == "prod"
        assert "memory" in parsed
        assert "resources" in parsed
        assert "watchdog" in parsed

    def test_optional_fields_omitted_when_empty(self):
        config = LauncherConfig(executable="app.pex")
        d = config.to_dict()
        assert "pythonPath" not in d
        assert "entryPoint" not in d
        assert "args" not in d
        assert "env" not in d
        assert "pythonOpts" not in d

    def test_dirs_default(self):
        config = LauncherConfig(executable="app.pex")
        d = config.to_dict()
        assert d["dirs"] == ["var/data/tmp", "var/log", "var/run"]

    def test_frozen_dataclass(self):
        config = LauncherConfig(executable="app.pex")
        with pytest.raises(AttributeError):
            config.executable = "other.pex"  # type: ignore[misc]


class TestCheckLauncherConfig:
    """Test CheckLauncherConfig for health check mode."""

    def test_basic_config(self):
        config = CheckLauncherConfig(
            executable="service/bin/app.pex",
            args=("--check",),
        )
        d = config.to_dict()
        assert d["configType"] == "python"
        assert d["configVersion"] == 1
        assert d["executable"] == "service/bin/app.pex"
        assert d["args"] == ["--check"]
        assert "entryPoint" not in d

    def test_with_entry_point(self):
        config = CheckLauncherConfig(
            executable="app.pex",
            args=("--health-check",),
            entry_point="myapp.health:check",
        )
        d = config.to_dict()
        assert d["entryPoint"] == "myapp.health:check"
        assert d["args"] == ["--health-check"]

    def test_to_yaml(self):
        config = CheckLauncherConfig(
            executable="app.pex",
            args=("--check", "--timeout", "5"),
        )
        yaml_str = config.to_yaml()
        parsed = yaml.safe_load(yaml_str)
        assert parsed["executable"] == "app.pex"
        assert parsed["args"] == ["--check", "--timeout", "5"]


class TestBuildLauncherConfig:
    """Test the factory function."""

    def test_basic_build(self):
        config = build_launcher_config(
            service_name="my-service",
            executable="service/bin/my-service.pex",
        )
        assert config.executable == "service/bin/my-service.pex"
        assert config.env["PYTHONDONTWRITEBYTECODE"] == "1"
        assert config.env["PYTHONUNBUFFERED"] == "1"

    def test_with_entry_point_and_args(self):
        config = build_launcher_config(
            service_name="my-service",
            executable="service/bin/my-service.pex",
            entry_point="app:main",
            args=("--port", "9090"),
        )
        assert config.entry_point == "app:main"
        assert config.args == ("--port", "9090")

    def test_env_merge(self):
        config = build_launcher_config(
            service_name="my-service",
            executable="app.pex",
            env={"CUSTOM_VAR": "value", "PYTHONDONTWRITEBYTECODE": "0"},
        )
        # User env overrides defaults
        assert config.env["CUSTOM_VAR"] == "value"
        assert config.env["PYTHONDONTWRITEBYTECODE"] == "0"
        assert config.env["PYTHONUNBUFFERED"] == "1"

    def test_no_extra_env(self):
        config = build_launcher_config(
            service_name="my-service",
            executable="app.pex",
        )
        assert len(config.env) == 2  # Just the two defaults


class TestBuildCheckLauncherConfig:
    """Test the check launcher factory."""

    def test_basic_build(self):
        config = build_check_launcher_config(
            executable="app.pex",
            check_args=("--check",),
        )
        assert config.executable == "app.pex"
        assert config.args == ("--check",)
        assert config.entry_point is None

    def test_with_entry_point(self):
        config = build_check_launcher_config(
            executable="app.pex",
            check_args=("--health",),
            entry_point="health:run",
        )
        assert config.entry_point == "health:run"
