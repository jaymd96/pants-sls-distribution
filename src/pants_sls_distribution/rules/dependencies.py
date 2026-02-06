"""SLS lock file generation rule."""

from __future__ import annotations

import logging
from dataclasses import dataclass

from pants.engine.rules import Get, collect_rules, rule

from pants_sls_distribution._lock_file import generate_lock_file
from pants_sls_distribution.rules.manifest import (
    SlsManifest,
    SlsManifestFieldSet,
    SlsManifestRequest,
)

logger = logging.getLogger(__name__)


# =============================================================================
# Request / Result types
# =============================================================================


@dataclass(frozen=True)
class SlsLockFileRequest:
    """Request to generate a product-dependencies.lock file."""

    field_set: SlsManifestFieldSet


@dataclass(frozen=True)
class SlsLockFileResult:
    """Result of lock file generation."""

    content: str
    product_id: str
    dependency_count: int


# =============================================================================
# Rules
# =============================================================================


@rule(desc="Generate SLS product-dependencies.lock")
async def generate_sls_lock_file(
    request: SlsLockFileRequest,
) -> SlsLockFileResult:
    # Generate the manifest to get resolved dependencies
    manifest = await Get(SlsManifest, SlsManifestRequest(request.field_set))

    deps = manifest.data.product_dependencies
    content = generate_lock_file(deps)

    logger.info(
        "Generated lock file for %s with %d dependencies",
        manifest.product_id,
        len(deps),
    )

    return SlsLockFileResult(
        content=content,
        product_id=manifest.product_id,
        dependency_count=len(deps),
    )


def rules():
    return collect_rules()
