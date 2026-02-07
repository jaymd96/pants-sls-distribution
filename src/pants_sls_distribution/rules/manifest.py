"""Manifest generation rule: sls_service target -> deployment/manifest.yml."""

from __future__ import annotations

import logging
from dataclasses import dataclass

import yaml

from pants.engine.addresses import Addresses, UnparsedAddressInputs
from pants.engine.rules import Get, MultiGet, collect_rules, rule
from pants.engine.target import (
    FieldSet,
    Targets,
    WrappedTarget,
    WrappedTargetRequest,
)

from pants_sls_distribution._exceptions import ManifestValidationError
from pants_sls_distribution._types import (
    Artifact,
    ManifestData,
    ProductDependency,
    ProductIncompatibility,
)
from pants_sls_distribution._validation import (
    resolve_default_max_version,
    validate_dependency,
    validate_manifest_identity,
    validate_replication,
)
from pants_sls_distribution.subsystem import SlsDistributionSubsystem
from pants_sls_distribution.targets import (
    AnnotationsField,
    ArtifactDigestField,
    ArtifactNameField,
    ArtifactsField,
    ArtifactTypeField,
    ArtifactUriField,
    CheckArgsField,
    CheckCommandField,
    CheckScriptField,
    DescriptionField,
    DisplayNameField,
    EntrypointField,
    EnvField,
    HooksField,
    LabelsField,
    ManifestExtensionsField,
    MaximumVersionField,
    MinimumVersionField,
    OptionalField,
    PexBinaryField,
    ProductDependenciesField,
    ProductGroupField,
    ProductIncompatibilitiesField,
    ProductNameField,
    ProductTypeField,
    PythonVersionField,
    ReasonField,
    RecommendedVersionField,
    ReplicationDesiredField,
    ReplicationMaxField,
    ReplicationMinField,
    ResourceLimitsField,
    ResourceRequestsField,
    ServiceArgsField,
    TraitsField,
    VersionField,
    VersionRangeField,
)

logger = logging.getLogger(__name__)


# =============================================================================
# Request / Result types
# =============================================================================


@dataclass(frozen=True)
class SlsManifestFieldSet(FieldSet):
    """Fields required to generate a manifest from an sls_service target."""

    required_fields = (ProductGroupField, ProductNameField, VersionField, EntrypointField)

    product_group: ProductGroupField
    product_name: ProductNameField
    version: VersionField
    product_type: ProductTypeField
    display_name: DisplayNameField
    description: DescriptionField
    entrypoint: EntrypointField
    args: ServiceArgsField
    env: EnvField
    python_version: PythonVersionField
    pex_binary: PexBinaryField
    hooks: HooksField
    check_args: CheckArgsField
    check_command: CheckCommandField
    check_script: CheckScriptField
    resource_requests: ResourceRequestsField
    resource_limits: ResourceLimitsField
    replication_desired: ReplicationDesiredField
    replication_min: ReplicationMinField
    replication_max: ReplicationMaxField
    labels: LabelsField
    annotations: AnnotationsField
    traits: TraitsField
    manifest_extensions: ManifestExtensionsField
    product_dependencies: ProductDependenciesField
    product_incompatibilities: ProductIncompatibilitiesField
    artifacts: ArtifactsField


@dataclass(frozen=True)
class SlsManifestRequest:
    field_set: SlsManifestFieldSet


@dataclass(frozen=True)
class SlsManifest:
    """Generated manifest content."""

    content: str
    product_id: str
    product_version: str
    data: ManifestData


# =============================================================================
# Rules
# =============================================================================


@rule(desc="Generate SLS manifest")
async def generate_manifest(
    request: SlsManifestRequest,
    subsystem: SlsDistributionSubsystem,
) -> SlsManifest:
    fs = request.field_set

    # --- Validate identity fields ---
    product_group = fs.product_group.value
    product_name = fs.product_name.value
    version = fs.version.value

    validate_manifest_identity(product_group, product_name, version)

    # Validate check field mutual exclusivity
    check_count = sum(
        1
        for v in [fs.check_args.value, fs.check_command.value, fs.check_script.value]
        if v is not None
    )
    if check_count > 1:
        raise ManifestValidationError(
            "Only one of check_args, check_command, or check_script may be set."
        )

    # --- Resolve product dependencies ---
    product_deps: tuple[ProductDependency, ...] = ()
    if fs.product_dependencies.value:
        dep_addresses = await Get(
            Addresses,
            UnparsedAddressInputs,
            fs.product_dependencies.to_unparsed_address_inputs(),
        )
        dep_targets_wrapped = await MultiGet(
            Get(WrappedTarget, WrappedTargetRequest(addr, description_of_origin="sls_service.product_dependencies"))
            for addr in dep_addresses
        )
        deps = []
        for wrapped in dep_targets_wrapped:
            t = wrapped.target
            dep = _resolve_product_dependency(t)
            validate_dependency(dep)
            deps.append(dep)
        product_deps = tuple(deps)

    # --- Resolve product incompatibilities ---
    product_incompats: tuple[ProductIncompatibility, ...] = ()
    if fs.product_incompatibilities.value:
        incompat_addresses = await Get(
            Addresses,
            UnparsedAddressInputs,
            fs.product_incompatibilities.to_unparsed_address_inputs(),
        )
        incompat_wrapped = await MultiGet(
            Get(WrappedTarget, WrappedTargetRequest(addr, description_of_origin="sls_service.product_incompatibilities"))
            for addr in incompat_addresses
        )
        product_incompats = tuple(
            ProductIncompatibility(
                product_group=w.target[ProductGroupField].value,
                product_name=w.target[ProductNameField].value,
                version_range=w.target[VersionRangeField].value,
                reason=w.target[ReasonField].value,
            )
            for w in incompat_wrapped
        )

    # --- Resolve artifacts ---
    artifacts: tuple[Artifact, ...] = ()
    if fs.artifacts.value:
        art_addresses = await Get(
            Addresses,
            UnparsedAddressInputs,
            fs.artifacts.to_unparsed_address_inputs(),
        )
        art_wrapped = await MultiGet(
            Get(WrappedTarget, WrappedTargetRequest(addr, description_of_origin="sls_service.artifacts"))
            for addr in art_addresses
        )
        artifacts = tuple(
            Artifact(
                type=w.target[ArtifactTypeField].value,
                uri=w.target[ArtifactUriField].value,
                name=w.target[ArtifactNameField].value,
                digest=w.target[ArtifactDigestField].value,
            )
            for w in art_wrapped
        )

    # --- Build replication dict ---
    replication: dict[str, int] = {}
    if fs.replication_desired.value is not None:
        replication["desired"] = fs.replication_desired.value
    if fs.replication_min.value is not None:
        replication["min"] = fs.replication_min.value
    if fs.replication_max.value is not None:
        replication["max"] = fs.replication_max.value

    if replication:
        validate_replication(replication)

    # --- Assemble manifest ---
    manifest_data = ManifestData(
        manifest_version=subsystem.manifest_version,
        product_type=fs.product_type.value or "helm.v1",
        product_group=product_group,
        product_name=product_name,
        product_version=version,
        display_name=fs.display_name.value,
        description=fs.description.value,
        traits=tuple(fs.traits.value or ()),
        labels=dict(fs.labels.value or {}),
        annotations=dict(fs.annotations.value or {}),
        resource_requests=dict(fs.resource_requests.value or {}),
        resource_limits=dict(fs.resource_limits.value or {}),
        replication=replication,
        product_dependencies=product_deps,
        product_incompatibilities=product_incompats,
        artifacts=artifacts,
        extensions=dict(fs.manifest_extensions.value or {}),
    )

    content = yaml.dump(
        manifest_data.to_dict(),
        default_flow_style=False,
        sort_keys=False,
        allow_unicode=True,
    )

    logger.info(
        "Generated manifest for %s:%s version %s",
        product_group,
        product_name,
        version,
    )

    return SlsManifest(
        content=content,
        product_id=manifest_data.product_id,
        product_version=version,
        data=manifest_data,
    )


# =============================================================================
# Helpers
# =============================================================================


def _resolve_product_dependency(target) -> ProductDependency:
    """Extract ProductDependency from an sls_product_dependency target."""
    max_version = target[MaximumVersionField].value
    min_version = target[MinimumVersionField].value

    # Default maximum version: derive <major>.x.x from minimum_version
    if max_version is None and min_version:
        max_version = resolve_default_max_version(min_version)

    return ProductDependency(
        product_group=target[ProductGroupField].value,
        product_name=target[ProductNameField].value,
        minimum_version=min_version,
        maximum_version=max_version,
        recommended_version=target[RecommendedVersionField].value,
        optional=target[OptionalField].value,
    )


def rules():
    return collect_rules()
