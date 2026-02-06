"""Tests for init script generation (pure functions, no Pants engine)."""

from __future__ import annotations

from pants_sls_distribution._init_script import generate_init_script


class TestGenerateInitScript:
    """Test init.sh generation."""

    def test_contains_shebang(self):
        script = generate_init_script(service_name="my-service")
        assert script.startswith("#!/bin/bash\n")

    def test_contains_service_name(self):
        script = generate_init_script(service_name="my-service")
        assert 'SERVICE_NAME="my-service"' in script

    def test_contains_all_commands(self):
        script = generate_init_script(service_name="test-svc")
        for cmd in ["start", "stop", "console", "status", "restart"]:
            assert f"do_{cmd}" in script
            assert f"    {cmd})" in script

    def test_contains_usage_message(self):
        script = generate_init_script(service_name="test-svc")
        assert "{start|stop|console|status|restart}" in script

    def test_contains_platform_detection(self):
        script = generate_init_script(service_name="test-svc")
        assert "detect_launcher" in script
        assert "uname -s" in script
        assert "uname -m" in script
        assert "amd64" in script
        assert "arm64" in script

    def test_contains_pid_file_management(self):
        script = generate_init_script(service_name="test-svc")
        assert "PID_FILE=" in script
        assert "is_running" in script

    def test_strict_mode(self):
        script = generate_init_script(service_name="test-svc")
        assert "set -euo pipefail" in script

    def test_custom_shutdown_timeout(self):
        script = generate_init_script(service_name="test-svc", shutdown_timeout=60)
        assert "-lt 60" in script

    def test_default_shutdown_timeout(self):
        script = generate_init_script(service_name="test-svc")
        assert "-lt 30" in script

    def test_creates_runtime_directories(self):
        script = generate_init_script(service_name="test-svc")
        assert "var/log" in script
        assert "var/run" in script
        assert "var/data/tmp" in script

    def test_launcher_binary_path_pattern(self):
        script = generate_init_script(service_name="test-svc")
        assert "go-python-launcher" in script

    def test_different_service_names(self):
        for name in ["alpha", "beta-service", "my.app"]:
            script = generate_init_script(service_name=name)
            assert f'SERVICE_NAME="{name}"' in script

    def test_graceful_shutdown_then_sigkill(self):
        script = generate_init_script(service_name="test-svc")
        assert "SIGTERM" in script or "kill -TERM" in script
        assert "SIGKILL" in script or "kill -KILL" in script

    def test_console_mode_uses_exec(self):
        script = generate_init_script(service_name="test-svc")
        assert 'exec "$LAUNCHER"' in script
