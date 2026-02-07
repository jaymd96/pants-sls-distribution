"""SLS publish rule: prepare release for Apollo Hub."""

from __future__ import annotations

import logging
import os
from dataclasses import dataclass

from pants.engine.rules import Get, collect_rules, rule

from pants_release_hub import (
    ApolloHubClient,
    PublishRequest,
    PublishResult,
    build_artifact_url,
)
from pants_sls_distribution.rules.manifest import (
    SlsManifest,
    SlsManifestFieldSet,
    SlsManifestRequest,
)
from pants_sls_distribution.subsystem import SlsDistributionSubsystem

logger = logging.getLogger(__name__)


# =============================================================================
# Request / Result types
# =============================================================================


@dataclass(frozen=True)
class SlsPublishRequest:
    """Request to publish an SLS distribution to Apollo Hub."""

    field_set: SlsManifestFieldSet
    dry_run: bool = False


@dataclass(frozen=True)
class SlsPublishResult:
    """Result of publishing to Apollo Hub."""

    result: PublishResult
    product_id: str
    product_version: str


# =============================================================================
# Rules
# =============================================================================


@rule(desc="Publish SLS distribution to Apollo Hub")
async def publish_sls_distribution(
    request: SlsPublishRequest,
    subsystem: SlsDistributionSubsystem,
) -> SlsPublishResult:
    # Generate the manifest
    manifest = await Get(SlsManifest, SlsManifestRequest(request.field_set))

    product_group = manifest.data.product_group
    product_name = manifest.data.product_name
    product_version = manifest.product_version

    # Build artifact URL
    artifact_url = build_artifact_url(
        registry=subsystem.docker_registry,
        product_name=product_name,
        product_version=product_version,
    )

    # Resolve channel
    channel = subsystem.publish_channel or None

    # Build publish request
    publish_request = PublishRequest(
        product_group=product_group,
        product_name=product_name,
        product_version=product_version,
        product_type=manifest.data.product_type,
        artifact_url=artifact_url,
        manifest_yaml=manifest.content,
        channel=channel,
        labels=dict(manifest.data.labels),
        dry_run=request.dry_run,
    )

    if request.dry_run:
        result = PublishResult.dry_run_result(publish_request)
    else:
        # Resolve auth token: subsystem option > environment variable
        auth_token = subsystem.apollo_auth_token or os.environ.get("APOLLO_AUTH_TOKEN") or None

        hub_url = subsystem.apollo_hub_url
        if not hub_url:
            result = PublishResult.failure(
                "apollo_hub_url not configured. Set [sls-distribution].apollo_hub_url in pants.toml"
            )
        else:
            client = ApolloHubClient(
                base_url=hub_url,
                auth_token=auth_token,
            )
            result = client.publish_release(publish_request)

    logger.info(
        "Publish %s: %s v%s -> %s",
        "dry-run" if request.dry_run else "result",
        manifest.product_id,
        product_version,
        result.message,
    )

    return SlsPublishResult(
        result=result,
        product_id=manifest.product_id,
        product_version=product_version,
    )


def rules():
    return collect_rules()
