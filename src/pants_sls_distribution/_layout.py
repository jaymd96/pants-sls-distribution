"""Pure Python SLS distribution layout assembly (no Pants dependencies).

Assembles the complete directory tree for an SLS distribution:

    <product-name>-<version>/
        deployment/
            manifest.yml
        service/
            bin/
                init.sh
                launcher-static.yml
                launcher-check.yml      (if check_args mode)
                <os>-<arch>/
                    python-service-launcher   (platform binaries)
            monitoring/
                bin/
                    check.sh            (if any check mode)
        var/
            data/tmp/
            log/
            run/
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass(frozen=True)
class LayoutFile:
    """A file to be placed in the SLS distribution layout."""

    relative_path: str  # Path relative to dist root
    content: str | None = None  # Text content (mutually exclusive with source_path)
    source_path: str | None = None  # Path to copy from (for binaries or user scripts)
    executable: bool = False  # Whether to set +x permission


@dataclass(frozen=True)
class LayoutDirectory:
    """A directory to create in the SLS distribution layout."""

    relative_path: str


@dataclass
class SlsLayout:
    """Complete SLS distribution layout specification.

    Collects all files and directories that make up the distribution.
    The actual I/O (writing files, creating dirs) is done by the Pants
    rule or packaging code that consumes this.
    """

    dist_name: str  # <product-name>-<version>
    files: list[LayoutFile] = field(default_factory=list)
    directories: list[LayoutDirectory] = field(default_factory=list)

    def add_file(
        self,
        relative_path: str,
        *,
        content: str | None = None,
        source_path: str | None = None,
        executable: bool = False,
    ) -> None:
        self.files.append(
            LayoutFile(
                relative_path=relative_path,
                content=content,
                source_path=source_path,
                executable=executable,
            )
        )

    def add_directory(self, relative_path: str) -> None:
        self.directories.append(LayoutDirectory(relative_path=relative_path))


def build_layout(
    *,
    product_name: str,
    product_version: str,
    manifest_yaml: str,
    launcher_static_yaml: str,
    init_script: str,
    check_script_content: str | None = None,
    check_script_source: str | None = None,
    launcher_check_yaml: str | None = None,
    lock_file_content: str | None = None,
    hook_entrypoint_content: str | None = None,
    hook_library_content: str | None = None,
    hook_startup_content: str | None = None,
    hook_scripts: dict[str, str] | None = None,
) -> SlsLayout:
    """Build the complete SLS distribution layout.

    Args:
        product_name: SLS product name.
        product_version: SLS product version.
        manifest_yaml: Content of deployment/manifest.yml.
        launcher_static_yaml: Content of service/bin/launcher-static.yml.
        init_script: Content of service/bin/init.sh.
        check_script_content: Generated check.sh content (check_args or check_command mode).
        check_script_source: Path to user-provided check.sh (check_script mode).
        launcher_check_yaml: Content of launcher-check.yml (check_args mode only).
        lock_file_content: Content of product-dependencies.lock (if deps exist).
        hook_entrypoint_content: Content of service/bin/entrypoint.sh (hook init system).
        hook_library_content: Content of service/lib/hooks.sh (hook library).
        hook_startup_content: Content of hooks/startup.d/00-main.sh (auto-generated).
        hook_scripts: User hook scripts as {hooks/<phase>.d/<name>.sh: source_path}.

    Returns:
        SlsLayout with all files and directories.
    """
    dist_name = f"{product_name}-{product_version}"
    layout = SlsLayout(dist_name=dist_name)

    # --- Runtime directories ---
    layout.add_directory("var/data/tmp")
    layout.add_directory("var/log")
    layout.add_directory("var/run")

    # --- deployment/ ---
    layout.add_file("deployment/manifest.yml", content=manifest_yaml)

    if lock_file_content is not None:
        layout.add_file("deployment/product-dependencies.lock", content=lock_file_content)

    # --- service/bin/ ---
    layout.add_file("service/bin/init.sh", content=init_script, executable=True)
    layout.add_file("service/bin/launcher-static.yml", content=launcher_static_yaml)

    # --- Launcher check config (check_args mode) ---
    if launcher_check_yaml is not None:
        layout.add_file("service/bin/launcher-check.yml", content=launcher_check_yaml)

    # --- service/monitoring/bin/check.sh ---
    if check_script_content is not None:
        layout.add_file(
            "service/monitoring/bin/check.sh",
            content=check_script_content,
            executable=True,
        )
    elif check_script_source is not None:
        layout.add_file(
            "service/monitoring/bin/check.sh",
            source_path=check_script_source,
            executable=True,
        )

    # --- Hook init system ---
    if hook_entrypoint_content is not None:
        layout.add_file(
            "service/bin/entrypoint.sh",
            content=hook_entrypoint_content,
            executable=True,
        )

    if hook_library_content is not None:
        layout.add_file("service/lib/hooks.sh", content=hook_library_content)

    if hook_entrypoint_content is not None:
        # Create all 7 hook phase directories
        from pants_sls_distribution._hooks import HOOK_PHASES

        for phase in HOOK_PHASES:
            layout.add_directory(f"hooks/{phase}.d")

        # State and metrics directories for the hook system
        layout.add_directory("var/state")
        layout.add_directory("var/metrics")

    if hook_startup_content is not None:
        layout.add_file(
            "hooks/startup.d/00-main.sh",
            content=hook_startup_content,
            executable=True,
        )

    if hook_scripts:
        for hook_path, source_path in hook_scripts.items():
            layout.add_file(
                f"hooks/{hook_path}",
                source_path=source_path,
                executable=True,
            )

    return layout


def layout_to_file_map(layout: SlsLayout) -> dict[str, str]:
    """Convert a layout to a flat dict of {relative_path: content}.

    Only includes files with inline content (not source_path references).
    Useful for testing and inspection.
    """
    result: dict[str, str] = {}
    for f in layout.files:
        if f.content is not None:
            result[f.relative_path] = f.content
    return result
