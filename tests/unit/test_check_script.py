"""Tests for check script generation (pure functions, no Pants engine)."""

from __future__ import annotations

import pytest

from pants_sls_distribution._check_script import (
    CheckMode,
    CheckScriptResult,
    generate_check_script,
)


class TestCheckMode:
    """Test CheckMode enum."""

    def test_values(self):
        assert CheckMode.CHECK_ARGS == "check_args"
        assert CheckMode.CHECK_COMMAND == "check_command"
        assert CheckMode.CHECK_SCRIPT == "check_script"
        assert CheckMode.NONE == "none"


class TestGenerateCheckScriptNone:
    """Test when no health check is configured."""

    def test_returns_none_mode(self):
        result = generate_check_script(service_name="my-svc")
        assert result.mode == CheckMode.NONE
        assert result.check_script_content is None
        assert result.source_path is None


class TestGenerateCheckScriptCheckArgs:
    """Test check_args mode (Palantir pattern)."""

    def test_basic_check_args(self):
        result = generate_check_script(
            service_name="my-svc",
            check_args=("--check",),
        )
        assert result.mode == CheckMode.CHECK_ARGS
        assert result.check_script_content is not None
        assert result.source_path is None

    def test_script_has_shebang(self):
        result = generate_check_script(
            service_name="my-svc",
            check_args=("--check",),
        )
        assert result.check_script_content.startswith("#!/bin/bash\n")

    def test_script_references_launcher_check(self):
        result = generate_check_script(
            service_name="my-svc",
            check_args=("--check",),
        )
        content = result.check_script_content
        assert "--check" in content
        assert "go-python-launcher" in content

    def test_script_contains_service_name(self):
        result = generate_check_script(
            service_name="my-svc",
            check_args=("--check",),
        )
        assert "my-svc" in result.check_script_content

    def test_script_detects_platform(self):
        result = generate_check_script(
            service_name="my-svc",
            check_args=("--check",),
        )
        content = result.check_script_content
        assert "uname" in content
        assert "amd64" in content
        assert "arm64" in content

    def test_script_strict_mode(self):
        result = generate_check_script(
            service_name="my-svc",
            check_args=("--check",),
        )
        assert "set -euo pipefail" in result.check_script_content


class TestGenerateCheckScriptCheckCommand:
    """Test check_command mode."""

    def test_basic_check_command(self):
        result = generate_check_script(
            service_name="my-svc",
            check_command="curl -f http://localhost:8080/health",
        )
        assert result.mode == CheckMode.CHECK_COMMAND
        assert result.check_script_content is not None

    def test_script_contains_command(self):
        result = generate_check_script(
            service_name="my-svc",
            check_command="python -m myapp.healthcheck",
        )
        assert "python -m myapp.healthcheck" in result.check_script_content

    def test_script_has_shebang(self):
        result = generate_check_script(
            service_name="my-svc",
            check_command="true",
        )
        assert result.check_script_content.startswith("#!/bin/bash\n")

    def test_script_uses_exec(self):
        result = generate_check_script(
            service_name="my-svc",
            check_command="curl -f http://localhost:8080/health",
        )
        assert "exec curl -f http://localhost:8080/health" in result.check_script_content


class TestGenerateCheckScriptCheckScript:
    """Test check_script mode (user-provided script)."""

    def test_returns_source_path(self):
        result = generate_check_script(
            service_name="my-svc",
            check_script_path="src/my_service/check.sh",
        )
        assert result.mode == CheckMode.CHECK_SCRIPT
        assert result.source_path == "src/my_service/check.sh"
        assert result.check_script_content is None


class TestMutualExclusivity:
    """Test that only one check mode can be set."""

    def test_check_args_and_check_command(self):
        with pytest.raises(ValueError, match="Only one"):
            generate_check_script(
                service_name="my-svc",
                check_args=("--check",),
                check_command="curl localhost",
            )

    def test_check_args_and_check_script(self):
        with pytest.raises(ValueError, match="Only one"):
            generate_check_script(
                service_name="my-svc",
                check_args=("--check",),
                check_script_path="check.sh",
            )

    def test_check_command_and_check_script(self):
        with pytest.raises(ValueError, match="Only one"):
            generate_check_script(
                service_name="my-svc",
                check_command="curl localhost",
                check_script_path="check.sh",
            )

    def test_all_three(self):
        with pytest.raises(ValueError, match="Only one"):
            generate_check_script(
                service_name="my-svc",
                check_args=("--check",),
                check_command="curl localhost",
                check_script_path="check.sh",
            )
