"""SLS Docker image build rule."""

from __future__ import annotations

import logging
from dataclasses import dataclass

from pants.engine.rules import Get, collect_rules, rule

from pants_sls_distribution._check_script import CheckMode, generate_check_script
from pants_sls_distribution._hooks import get_entrypoint_script, get_hooks_library
from pants_docker_generator import Dockerfile, sls_dockerfile, sls_dockerignore
from pants_sls_distribution.rules.manifest import SlsManifestFieldSet
from pants_sls_distribution.rules.package import (
    SlsPackageRequest,
    SlsPackageResult,
)
from pants_sls_distribution.subsystem import SlsDistributionSubsystem
from pants_sls_distribution.targets import (
    CheckArgsField,
    CheckCommandField,
    CheckScriptField,
    HooksField,
)

logger = logging.getLogger(__name__)


# =============================================================================
# Request / Result types
# =============================================================================


@dataclass(frozen=True)
class SlsDockerRequest:
    """Request to build a Docker image for an SLS distribution."""

    field_set: SlsManifestFieldSet


@dataclass(frozen=True)
class SlsDockerResult:
    """Result of Docker image generation (Dockerfile + context)."""

    dockerfile_content: str
    dockerignore_content: str
    dockerfile: Dockerfile
    package_result: SlsPackageResult
    hook_entrypoint_content: str | None = None
    hook_library_content: str | None = None


# =============================================================================
# Rules
# =============================================================================


@rule(desc="Generate SLS Docker image configuration")
async def generate_docker_config(
    request: SlsDockerRequest,
    subsystem: SlsDistributionSubsystem,
) -> SlsDockerResult:
    fs = request.field_set

    # Get the packaged SLS distribution
    package_result = await Get(
        SlsPackageResult,
        SlsPackageRequest(fs),
    )

    product_name = package_result.product_name
    product_version = package_result.product_version
    dist_name = package_result.dist_name
    tarball_name = f"{dist_name}.sls.tgz"

    # Determine if health check is configured
    check_args = fs.check_args.value
    check_command = fs.check_command.value
    check_script_path = fs.check_script.value
    has_health_check = any(v is not None for v in [check_args, check_command, check_script_path])

    # Determine if hook init system is enabled
    hooks = fs.hooks.value
    use_hook_init = bool(hooks)

    hook_entrypoint_content = None
    hook_library_content = None
    if use_hook_init:
        hook_entrypoint_content = get_entrypoint_script()
        hook_library_content = get_hooks_library()

    dockerfile = sls_dockerfile(
        base_image=subsystem.docker_base_image,
        product_name=product_name,
        product_version=product_version,
        product_group=package_result.manifest.data.product_group,
        dist_name=dist_name,
        tarball_name=tarball_name,
        install_path=subsystem.install_path,
        product_type=package_result.manifest.data.product_type,
        health_check_interval=10 if has_health_check else None,
        health_check_timeout=5 if has_health_check else None,
        use_hook_init=use_hook_init,
    )

    dockerfile_content = dockerfile.render()
    dockerignore_content = sls_dockerignore()

    image_tag = f"{product_name}:{product_version}"
    logger.info("Generated Docker config for %s", image_tag)

    return SlsDockerResult(
        dockerfile_content=dockerfile_content,
        dockerignore_content=dockerignore_content,
        dockerfile=dockerfile,
        package_result=package_result,
        hook_entrypoint_content=hook_entrypoint_content,
        hook_library_content=hook_library_content,
    )


def rules():
    return collect_rules()
