"""SLS packaging rule: assemble layout and create tarball."""

from __future__ import annotations

import logging
from dataclasses import dataclass

from pants.engine.fs import Digest
from pants.engine.rules import Get, collect_rules, rule

from pants_sls_distribution._check_script import CheckMode, generate_check_script
from pants_sls_distribution._hooks import (
    generate_startup_script,
    get_entrypoint_script,
    get_hooks_library,
    validate_hook_paths,
)
from pants_sls_distribution._init_script import generate_init_script
from pants_sls_distribution._launcher_config import (
    build_check_launcher_config,
    build_launcher_config,
)
from pants_sls_distribution._layout import SlsLayout, build_layout
from pants_sls_distribution._lock_file import generate_lock_file
from pants_sls_distribution.rules.launcher import (
    LauncherBinariesRequest,
    LauncherBinariesResult,
)
from pants_sls_distribution.rules.manifest import (
    SlsManifest,
    SlsManifestFieldSet,
    SlsManifestRequest,
)
from pants_sls_distribution.targets import (
    CheckArgsField,
    CheckCommandField,
    CheckScriptField,
    EntrypointField,
    EnvField,
    HooksField,
    PexBinaryField,
    PythonVersionField,
    ServiceArgsField,
)

logger = logging.getLogger(__name__)


# =============================================================================
# Request / Result types
# =============================================================================


@dataclass(frozen=True)
class SlsPackageRequest:
    """Request to assemble an SLS distribution layout."""

    field_set: SlsManifestFieldSet


@dataclass(frozen=True)
class SlsPackageResult:
    """Result of SLS layout assembly."""

    layout: SlsLayout
    manifest: SlsManifest
    product_name: str
    product_version: str
    dist_name: str
    launcher_digest: Digest


# =============================================================================
# Rules
# =============================================================================


@rule(desc="Assemble SLS distribution layout")
async def assemble_sls_package(
    request: SlsPackageRequest,
) -> SlsPackageResult:
    fs = request.field_set

    # Generate the manifest first
    manifest = await Get(SlsManifest, SlsManifestRequest(fs))

    product_name = manifest.data.product_name
    product_version = manifest.product_version

    # --- Build launcher config ---
    entrypoint = fs.entrypoint.value
    pex_binary = fs.pex_binary.value if hasattr(fs, "pex_binary") else None
    executable = pex_binary or f"service/bin/{product_name}.pex"

    launcher_config = build_launcher_config(
        service_name=product_name,
        executable=executable,
        entry_point=entrypoint,
        args=tuple(fs.args.value or ()),
        env=dict(fs.env.value) if fs.env.value else None,
        python_version=fs.python_version.value or "3.11",
    )

    # --- Generate init script ---
    init_script = generate_init_script(service_name=product_name)

    # --- Generate check script ---
    check_args = fs.check_args.value
    check_command = fs.check_command.value
    check_script_path = fs.check_script.value

    check_result = generate_check_script(
        service_name=product_name,
        check_args=tuple(check_args) if check_args else None,
        check_command=check_command,
        check_script_path=check_script_path,
    )

    # Build launcher-check.yml if check_args mode
    launcher_check_yaml = None
    if check_result.mode == CheckMode.CHECK_ARGS and check_args:
        check_launcher = build_check_launcher_config(
            executable=executable,
            check_args=tuple(check_args),
            entry_point=entrypoint,
        )
        launcher_check_yaml = check_launcher.to_yaml()

    # --- Generate lock file (if dependencies exist) ---
    lock_file_content = None
    if manifest.data.product_dependencies:
        lock_file_content = generate_lock_file(manifest.data.product_dependencies)

    # --- Hook init system ---
    hooks = fs.hooks.value
    hook_entrypoint_content = None
    hook_library_content = None
    hook_startup_content = None
    hook_scripts: dict[str, str] | None = None

    if hooks:
        validate_hook_paths(hooks)
        hook_entrypoint_content = get_entrypoint_script()
        hook_library_content = get_hooks_library()
        hook_startup_content = generate_startup_script(product_name)
        hook_scripts = dict(hooks)

    # --- Download launcher binaries ---
    launcher_result = await Get(LauncherBinariesResult, LauncherBinariesRequest())

    # --- Assemble layout ---
    layout = build_layout(
        product_name=product_name,
        product_version=product_version,
        manifest_yaml=manifest.content,
        launcher_static_yaml=launcher_config.to_yaml(),
        init_script=init_script,
        check_script_content=check_result.check_script_content,
        check_script_source=check_result.source_path,
        launcher_check_yaml=launcher_check_yaml,
        lock_file_content=lock_file_content,
        hook_entrypoint_content=hook_entrypoint_content,
        hook_library_content=hook_library_content,
        hook_startup_content=hook_startup_content,
        hook_scripts=hook_scripts,
    )

    dist_name = f"{product_name}-{product_version}"

    logger.info("Assembled SLS layout for %s", dist_name)

    return SlsPackageResult(
        layout=layout,
        manifest=manifest,
        product_name=product_name,
        product_version=product_version,
        dist_name=dist_name,
        launcher_digest=launcher_result.digest,
    )


def rules():
    return collect_rules()
