"""Tests for SLS layout assembly (pure functions, no Pants engine)."""

from __future__ import annotations

from pants_sls_distribution._layout import (
    LayoutFile,
    SlsLayout,
    build_layout,
    layout_to_file_map,
)


class TestSlsLayout:
    """Test SlsLayout data structure."""

    def test_add_file_with_content(self):
        layout = SlsLayout(dist_name="my-svc-1.0.0")
        layout.add_file("deployment/manifest.yml", content="manifest-version: '1.0'\n")
        assert len(layout.files) == 1
        assert layout.files[0].relative_path == "deployment/manifest.yml"
        assert layout.files[0].content == "manifest-version: '1.0'\n"
        assert layout.files[0].source_path is None

    def test_add_file_with_source(self):
        layout = SlsLayout(dist_name="my-svc-1.0.0")
        layout.add_file("service/monitoring/bin/check.sh", source_path="/path/to/check.sh", executable=True)
        assert len(layout.files) == 1
        assert layout.files[0].source_path == "/path/to/check.sh"
        assert layout.files[0].executable is True

    def test_add_directory(self):
        layout = SlsLayout(dist_name="my-svc-1.0.0")
        layout.add_directory("var/log")
        assert len(layout.directories) == 1
        assert layout.directories[0].relative_path == "var/log"

    def test_dist_name(self):
        layout = SlsLayout(dist_name="my-svc-2.0.0")
        assert layout.dist_name == "my-svc-2.0.0"


class TestBuildLayout:
    """Test the build_layout factory function."""

    def test_basic_layout(self):
        layout = build_layout(
            product_name="my-svc",
            product_version="1.0.0",
            manifest_yaml="manifest-version: '1.0'\n",
            launcher_static_yaml="configType: python\n",
            init_script="#!/bin/bash\n",
        )
        assert layout.dist_name == "my-svc-1.0.0"

    def test_contains_manifest(self):
        layout = build_layout(
            product_name="my-svc",
            product_version="1.0.0",
            manifest_yaml="manifest content",
            launcher_static_yaml="launcher content",
            init_script="init content",
        )
        files = {f.relative_path: f for f in layout.files}
        assert "deployment/manifest.yml" in files
        assert files["deployment/manifest.yml"].content == "manifest content"

    def test_contains_launcher_static(self):
        layout = build_layout(
            product_name="my-svc",
            product_version="1.0.0",
            manifest_yaml="m",
            launcher_static_yaml="launcher content",
            init_script="i",
        )
        files = {f.relative_path: f for f in layout.files}
        assert "service/bin/launcher-static.yml" in files
        assert files["service/bin/launcher-static.yml"].content == "launcher content"

    def test_contains_init_script(self):
        layout = build_layout(
            product_name="my-svc",
            product_version="1.0.0",
            manifest_yaml="m",
            launcher_static_yaml="l",
            init_script="#!/bin/bash\necho hello",
        )
        files = {f.relative_path: f for f in layout.files}
        assert "service/bin/init.sh" in files
        assert files["service/bin/init.sh"].executable is True

    def test_runtime_directories(self):
        layout = build_layout(
            product_name="my-svc",
            product_version="1.0.0",
            manifest_yaml="m",
            launcher_static_yaml="l",
            init_script="i",
        )
        dir_paths = {d.relative_path for d in layout.directories}
        assert "var/data/tmp" in dir_paths
        assert "var/log" in dir_paths
        assert "var/run" in dir_paths

    def test_with_check_script_content(self):
        layout = build_layout(
            product_name="my-svc",
            product_version="1.0.0",
            manifest_yaml="m",
            launcher_static_yaml="l",
            init_script="i",
            check_script_content="#!/bin/bash\ncurl localhost",
        )
        files = {f.relative_path: f for f in layout.files}
        assert "service/monitoring/bin/check.sh" in files
        assert files["service/monitoring/bin/check.sh"].executable is True
        assert files["service/monitoring/bin/check.sh"].content == "#!/bin/bash\ncurl localhost"

    def test_with_check_script_source(self):
        layout = build_layout(
            product_name="my-svc",
            product_version="1.0.0",
            manifest_yaml="m",
            launcher_static_yaml="l",
            init_script="i",
            check_script_source="/path/to/check.sh",
        )
        files = {f.relative_path: f for f in layout.files}
        assert "service/monitoring/bin/check.sh" in files
        assert files["service/monitoring/bin/check.sh"].source_path == "/path/to/check.sh"

    def test_with_launcher_check_yaml(self):
        layout = build_layout(
            product_name="my-svc",
            product_version="1.0.0",
            manifest_yaml="m",
            launcher_static_yaml="l",
            init_script="i",
            launcher_check_yaml="configType: python\nargs: ['--check']",
        )
        files = {f.relative_path: f for f in layout.files}
        assert "service/bin/launcher-check.yml" in files

    def test_no_check_by_default(self):
        layout = build_layout(
            product_name="my-svc",
            product_version="1.0.0",
            manifest_yaml="m",
            launcher_static_yaml="l",
            init_script="i",
        )
        files = {f.relative_path for f in layout.files}
        assert "service/monitoring/bin/check.sh" not in files
        assert "service/bin/launcher-check.yml" not in files


class TestLayoutToFileMap:
    """Test the layout_to_file_map helper."""

    def test_only_content_files(self):
        layout = SlsLayout(dist_name="test-1.0.0")
        layout.add_file("a.txt", content="hello")
        layout.add_file("b.txt", source_path="/some/path")
        layout.add_file("c.txt", content="world")

        result = layout_to_file_map(layout)
        assert result == {"a.txt": "hello", "c.txt": "world"}

    def test_empty_layout(self):
        layout = SlsLayout(dist_name="test-1.0.0")
        assert layout_to_file_map(layout) == {}


class TestFullLayoutIntegration:
    """Integration test: build a complete layout with all check modes."""

    def test_check_args_mode_layout(self):
        """check_args mode produces launcher-check.yml AND check.sh."""
        layout = build_layout(
            product_name="my-svc",
            product_version="2.1.0",
            manifest_yaml="manifest-version: '1.0'\n",
            launcher_static_yaml="configType: python\n",
            init_script="#!/bin/bash\n",
            check_script_content="#!/bin/bash\nexec launcher --check\n",
            launcher_check_yaml="configType: python\nargs: ['--check']\n",
        )

        file_paths = {f.relative_path for f in layout.files}
        assert "deployment/manifest.yml" in file_paths
        assert "service/bin/init.sh" in file_paths
        assert "service/bin/launcher-static.yml" in file_paths
        assert "service/bin/launcher-check.yml" in file_paths
        assert "service/monitoring/bin/check.sh" in file_paths

        # Verify dist name
        assert layout.dist_name == "my-svc-2.1.0"

        # Verify runtime dirs
        dir_paths = {d.relative_path for d in layout.directories}
        assert len(dir_paths) == 3

    def test_check_command_mode_layout(self):
        """check_command mode produces only check.sh, no launcher-check.yml."""
        layout = build_layout(
            product_name="api-svc",
            product_version="1.0.0",
            manifest_yaml="m",
            launcher_static_yaml="l",
            init_script="i",
            check_script_content="#!/bin/bash\ncurl -f http://localhost:8080/health\n",
        )

        file_paths = {f.relative_path for f in layout.files}
        assert "service/monitoring/bin/check.sh" in file_paths
        assert "service/bin/launcher-check.yml" not in file_paths

    def test_no_check_mode_layout(self):
        """No check mode produces no check files."""
        layout = build_layout(
            product_name="worker-svc",
            product_version="3.0.0",
            manifest_yaml="m",
            launcher_static_yaml="l",
            init_script="i",
        )

        file_paths = {f.relative_path for f in layout.files}
        assert "service/monitoring/bin/check.sh" not in file_paths
        assert "service/bin/launcher-check.yml" not in file_paths
        # Should still have the core 3 files
        assert "deployment/manifest.yml" in file_paths
        assert "service/bin/init.sh" in file_paths
        assert "service/bin/launcher-static.yml" in file_paths


class TestHookLayoutIntegration:
    """Test hook init system layout integration."""

    _HOOK_KWARGS = dict(
        product_name="my-svc",
        product_version="1.0.0",
        manifest_yaml="m",
        launcher_static_yaml="l",
        init_script="i",
        hook_entrypoint_content="#!/bin/sh\n# entrypoint",
        hook_library_content="#!/bin/sh\n# hooks library",
        hook_startup_content="#!/bin/sh\n# startup",
    )

    def test_with_hooks_creates_entrypoint(self):
        """entrypoint.sh placed at service/bin/."""
        layout = build_layout(**self._HOOK_KWARGS)
        files = {f.relative_path: f for f in layout.files}
        assert "service/bin/entrypoint.sh" in files
        assert files["service/bin/entrypoint.sh"].executable is True
        assert files["service/bin/entrypoint.sh"].content == "#!/bin/sh\n# entrypoint"

    def test_with_hooks_creates_library(self):
        """hooks.sh placed at service/lib/."""
        layout = build_layout(**self._HOOK_KWARGS)
        files = {f.relative_path: f for f in layout.files}
        assert "service/lib/hooks.sh" in files
        assert files["service/lib/hooks.sh"].content == "#!/bin/sh\n# hooks library"

    def test_with_hooks_creates_phase_dirs(self):
        """All 7 hook phase directories are created."""
        layout = build_layout(**self._HOOK_KWARGS)
        dir_paths = {d.relative_path for d in layout.directories}
        expected_phases = (
            "pre-configure", "configure", "pre-startup", "startup",
            "post-startup", "pre-shutdown", "shutdown",
        )
        for phase in expected_phases:
            assert f"hooks/{phase}.d" in dir_paths, f"Missing hooks/{phase}.d"

    def test_with_hooks_creates_startup_script(self):
        """00-main.sh is executable at hooks/startup.d/."""
        layout = build_layout(**self._HOOK_KWARGS)
        files = {f.relative_path: f for f in layout.files}
        assert "hooks/startup.d/00-main.sh" in files
        assert files["hooks/startup.d/00-main.sh"].executable is True

    def test_with_hooks_adds_user_scripts(self):
        """User hook scripts are added with source_path."""
        layout = build_layout(
            **self._HOOK_KWARGS,
            hook_scripts={
                "pre-startup.d/10-migrate.sh": "hooks/migrate.sh",
                "post-startup.d/10-warm.sh": "hooks/warm.sh",
            },
        )
        files = {f.relative_path: f for f in layout.files}
        assert "hooks/pre-startup.d/10-migrate.sh" in files
        assert files["hooks/pre-startup.d/10-migrate.sh"].source_path == "hooks/migrate.sh"
        assert files["hooks/pre-startup.d/10-migrate.sh"].executable is True
        assert "hooks/post-startup.d/10-warm.sh" in files
        assert files["hooks/post-startup.d/10-warm.sh"].source_path == "hooks/warm.sh"

    def test_with_hooks_creates_state_dir(self):
        """var/state directory exists for hook system."""
        layout = build_layout(**self._HOOK_KWARGS)
        dir_paths = {d.relative_path for d in layout.directories}
        assert "var/state" in dir_paths

    def test_with_hooks_creates_metrics_dir(self):
        """var/metrics directory exists for hook system."""
        layout = build_layout(**self._HOOK_KWARGS)
        dir_paths = {d.relative_path for d in layout.directories}
        assert "var/metrics" in dir_paths

    def test_without_hooks_unchanged(self):
        """No hook files when hooks are not provided."""
        layout = build_layout(
            product_name="my-svc",
            product_version="1.0.0",
            manifest_yaml="m",
            launcher_static_yaml="l",
            init_script="i",
        )
        file_paths = {f.relative_path for f in layout.files}
        dir_paths = {d.relative_path for d in layout.directories}

        assert "service/bin/entrypoint.sh" not in file_paths
        assert "service/lib/hooks.sh" not in file_paths
        assert "hooks/startup.d/00-main.sh" not in file_paths
        assert "var/state" not in dir_paths
        assert "var/metrics" not in dir_paths
        # Still has the base 3 dirs
        assert dir_paths == {"var/data/tmp", "var/log", "var/run"}
