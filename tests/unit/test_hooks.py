"""Tests for hook init system integration (pure functions, no Pants engine)."""

from __future__ import annotations

import pytest

from pants_sls_distribution._hooks import (
    HOOK_PHASES,
    generate_startup_script,
    get_entrypoint_script,
    get_hooks_library,
    validate_hook_paths,
)


class TestHookPhases:
    """Test HOOK_PHASES constant."""

    def test_hook_phases_complete(self):
        """All 7 lifecycle phases are defined."""
        assert len(HOOK_PHASES) == 7
        assert HOOK_PHASES == (
            "pre-configure",
            "configure",
            "pre-startup",
            "startup",
            "post-startup",
            "pre-shutdown",
            "shutdown",
        )


class TestValidateHookPaths:
    """Test validate_hook_paths()."""

    def test_valid_paths(self):
        """Accepts valid <phase>.d/<name>.sh keys."""
        hooks = {
            "pre-startup.d/10-migrate.sh": "hooks/migrate.sh",
            "post-startup.d/10-warm-cache.sh": "hooks/warm-cache.sh",
            "pre-shutdown.d/10-drain.sh": "hooks/drain.sh",
            "configure.d/00-setup.sh": "hooks/setup.sh",
            "startup.d/99-custom.sh": "hooks/custom.sh",
            "pre-configure.d/01-check.sh": "hooks/check.sh",
            "shutdown.d/50-cleanup.sh": "hooks/cleanup.sh",
        }
        # Should not raise
        validate_hook_paths(hooks)

    def test_invalid_phase(self):
        """Rejects unknown phase names."""
        hooks = {"invalid-phase.d/10-test.sh": "hooks/test.sh"}
        with pytest.raises(ValueError, match="Unknown hook phase 'invalid-phase'"):
            validate_hook_paths(hooks)

    def test_invalid_format_no_dot_d(self):
        """Rejects keys without .d/ separator."""
        hooks = {"pre-startup/10-migrate.sh": "hooks/migrate.sh"}
        with pytest.raises(ValueError, match="must match"):
            validate_hook_paths(hooks)

    def test_invalid_format_no_sh_extension(self):
        """Rejects keys without .sh extension."""
        hooks = {"pre-startup.d/10-migrate": "hooks/migrate.sh"}
        with pytest.raises(ValueError, match="must match"):
            validate_hook_paths(hooks)

    def test_invalid_format_empty_name(self):
        """Rejects keys with empty script name."""
        hooks = {"pre-startup.d/.sh": "hooks/migrate.sh"}
        with pytest.raises(ValueError, match="must match"):
            validate_hook_paths(hooks)

    def test_empty_hooks(self):
        """Empty dict is valid (no hooks to validate)."""
        validate_hook_paths({})

    def test_valid_names_with_dots_and_underscores(self):
        """Script names can contain dots, underscores, and hyphens."""
        hooks = {
            "pre-startup.d/10_db.migrate.sh": "hooks/migrate.sh",
            "configure.d/01-setup_env.sh": "hooks/setup.sh",
        }
        validate_hook_paths(hooks)


class TestGenerateStartupScript:
    """Test generate_startup_script()."""

    def test_contains_service_name(self):
        script = generate_startup_script("my-service")
        assert "my-service" in script

    def test_writes_pid(self):
        script = generate_startup_script("my-service")
        assert "main.pid" in script
        assert "echo $!" in script

    def test_detects_platform(self):
        """Script includes platform detection for launcher binary."""
        script = generate_startup_script("my-service")
        assert "uname -s" in script
        assert "uname -m" in script
        assert "amd64" in script
        assert "arm64" in script

    def test_uses_service_root(self):
        script = generate_startup_script("my-service")
        assert "${SERVICE_ROOT}" in script

    def test_is_posix_shell(self):
        """Script starts with #!/bin/sh."""
        script = generate_startup_script("my-service")
        assert script.startswith("#!/bin/sh\n")


class TestGetEntrypointScript:
    """Test get_entrypoint_script()."""

    def test_not_empty(self):
        content = get_entrypoint_script()
        assert len(content) > 0

    def test_is_posix_shell(self):
        content = get_entrypoint_script()
        assert content.startswith("#!/bin/sh\n")

    def test_auto_detects_service_root(self):
        """SERVICE_ROOT defaults to auto-detected path from script location."""
        content = get_entrypoint_script()
        assert 'SERVICE_ROOT="${SERVICE_ROOT:-$(cd "$SCRIPT_DIR/../.." && pwd)}"' in content

    def test_sources_hooks_library(self):
        content = get_entrypoint_script()
        assert "hooks.sh" in content

    def test_contains_all_phases(self):
        content = get_entrypoint_script()
        for phase in HOOK_PHASES:
            assert phase in content

    def test_signal_handling(self):
        content = get_entrypoint_script()
        assert "trap _shutdown TERM INT" in content


class TestGetHooksLibrary:
    """Test get_hooks_library()."""

    def test_not_empty(self):
        content = get_hooks_library()
        assert len(content) > 0

    def test_is_posix_shell(self):
        content = get_hooks_library()
        assert content.startswith("#!/bin/sh\n")

    def test_provides_run_hooks(self):
        content = get_hooks_library()
        assert "run_hooks()" in content

    def test_provides_run_hooks_timed(self):
        content = get_hooks_library()
        assert "run_hooks_timed()" in content

    def test_provides_run_hooks_warn(self):
        content = get_hooks_library()
        assert "run_hooks_warn()" in content
