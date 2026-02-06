"""SLS distribution target types for Pants BUILD files.

Provides:
  - sls_service: Python service packaged as SLS distribution
  - sls_product_dependency: Product dependency declaration
  - sls_product_incompatibility: Product incompatibility declaration
  - sls_artifact: Artifact reference (OCI image, etc.)
"""

from __future__ import annotations

from pants.engine.target import (
    COMMON_TARGET_FIELDS,
    BoolField,
    DictStringToStringField,
    IntField,
    MultipleSourcesField,
    SpecialCasedDependencies,
    StringField,
    StringSequenceField,
    Target,
)
from pants.util.strutil import softwrap


# =============================================================================
# Core identity fields
# =============================================================================


class ProductGroupField(StringField):
    alias = "product_group"
    required = True
    help = softwrap(
        """
        Maven-style product group identifier (e.g., 'com.example').
        Must be lowercase letters, digits, dots, and hyphens.
        """
    )


class ProductNameField(StringField):
    alias = "product_name"
    required = True
    help = softwrap(
        """
        Product name (e.g., 'my-service').
        Must start with a lowercase letter; allows lowercase letters, digits, dots, hyphens.
        """
    )


class VersionField(StringField):
    alias = "version"
    required = True
    help = softwrap(
        """
        SLS orderable version. Supported formats:
        X.Y.Z, X.Y.Z-rcN, X.Y.Z-N-gHASH, X.Y.Z-rcN-N-gHASH
        """
    )


class DisplayNameField(StringField):
    alias = "display_name"
    default = None
    help = "Human-readable display name for the product."


class DescriptionField(StringField):
    alias = "description"
    default = None
    help = "Product description."


class ProductTypeField(StringField):
    alias = "product_type"
    default = "helm.v1"
    help = softwrap(
        """
        SLS product type. One of: helm.v1, asset.v1, service.v1.
        Defaults to helm.v1 (Python service wrapped in Helm chart for K8s).
        """
    )


# =============================================================================
# Python service configuration fields
# =============================================================================


class EntrypointField(StringField):
    alias = "entrypoint"
    required = True
    help = softwrap(
        """
        Python entrypoint in module:callable format (e.g., 'app:app' for ASGI).
        This is baked into the launcher configuration.
        """
    )


class CommandField(StringField):
    alias = "command"
    default = "uvicorn"
    help = "Command to run the service. Default: uvicorn."


class ServiceArgsField(StringSequenceField):
    alias = "args"
    default = ("--host", "0.0.0.0", "--port", "8080")
    help = "Arguments passed to the service command."


class PythonVersionField(StringField):
    alias = "python_version"
    default = "3.11"
    help = "Python version requirement for the service."


class EnvField(DictStringToStringField):
    alias = "env"
    help = "Environment variables set when launching the service."


class PexBinaryField(StringField):
    alias = "pex_binary"
    default = None
    help = softwrap(
        """
        Path to the PEX binary relative to the distribution root.
        If set, the python-service-launcher will execute this PEX directly
        instead of using command + entrypoint.
        """
    )


# =============================================================================
# Health check fields (mutually exclusive modes)
# =============================================================================


class CheckArgsField(StringSequenceField):
    alias = "check_args"
    default = None
    help = softwrap(
        """
        Arguments for health check using the Palantir pattern: same binary, different args.
        Generates a launcher-check.yml that runs the PEX with these args.
        Mutually exclusive with check_command and check_script.
        """
    )


class CheckCommandField(StringField):
    alias = "check_command"
    default = None
    help = softwrap(
        """
        Custom command for health check (e.g., 'python -m myservice.healthcheck').
        Generates a check.sh that runs this command.
        Mutually exclusive with check_args and check_script.
        """
    )


class CheckScriptField(StringField):
    alias = "check_script"
    default = None
    help = softwrap(
        """
        Path to a custom check.sh script provided by the developer.
        The script is copied verbatim to service/monitoring/bin/check.sh.
        Mutually exclusive with check_args and check_command.
        """
    )


# =============================================================================
# Resource and replication fields
# =============================================================================


class ResourceRequestsField(DictStringToStringField):
    alias = "resource_requests"
    help = "Kubernetes resource requests (e.g., {'cpu': '100m', 'memory': '128Mi'})."


class ResourceLimitsField(DictStringToStringField):
    alias = "resource_limits"
    help = "Kubernetes resource limits (e.g., {'cpu': '500m', 'memory': '512Mi'})."


class ReplicationDesiredField(IntField):
    alias = "replication_desired"
    default = None
    help = "Desired replica count."


class ReplicationMinField(IntField):
    alias = "replication_min"
    default = None
    help = "Minimum replica count."


class ReplicationMaxField(IntField):
    alias = "replication_max"
    default = None
    help = "Maximum replica count."


# =============================================================================
# Metadata fields
# =============================================================================


class LabelsField(DictStringToStringField):
    alias = "labels"
    help = "Labels applied to the product (e.g., {'team': 'platform'})."


class AnnotationsField(DictStringToStringField):
    alias = "annotations"
    help = "Annotations applied to the product."


class TraitsField(StringSequenceField):
    alias = "traits"
    default = ()
    help = "Capability traits (e.g., ['api', 'web'])."


class ManifestExtensionsField(DictStringToStringField):
    alias = "manifest_extensions"
    help = "Additional manifest extension fields."


# =============================================================================
# Dependency reference fields
# =============================================================================


class ProductDependenciesField(SpecialCasedDependencies):
    alias = "product_dependencies"
    help = "References to sls_product_dependency targets."


class ProductIncompatibilitiesField(SpecialCasedDependencies):
    alias = "product_incompatibilities"
    help = "References to sls_product_incompatibility targets."


class ArtifactsField(SpecialCasedDependencies):
    alias = "artifacts"
    help = "References to sls_artifact targets."


# =============================================================================
# Source fields
# =============================================================================


class SlsServiceSourcesField(MultipleSourcesField):
    default = ("**/*.py",)
    expected_file_extensions = (".py", ".pyi")
    help = "Python source files for the service."


# =============================================================================
# Product dependency target fields
# =============================================================================


class MinimumVersionField(StringField):
    alias = "minimum_version"
    required = True
    help = "Minimum compatible version of the dependency."


class MaximumVersionField(StringField):
    alias = "maximum_version"
    default = None
    help = softwrap(
        """
        Maximum compatible version (e.g., '2.0.0' or '1.x.x').
        If omitted, defaults to '<major>.x.x' derived from minimum_version.
        """
    )


class RecommendedVersionField(StringField):
    alias = "recommended_version"
    default = None
    help = "Recommended version of the dependency."


class OptionalField(BoolField):
    alias = "optional"
    default = False
    help = "Whether this dependency is optional."


# =============================================================================
# Product incompatibility target fields
# =============================================================================


class VersionRangeField(StringField):
    alias = "version_range"
    required = True
    help = "Version range that is incompatible (e.g., '< 2.0.0')."


class ReasonField(StringField):
    alias = "reason"
    required = True
    help = "Explanation for the incompatibility."


# =============================================================================
# Artifact target fields
# =============================================================================


class ArtifactTypeField(StringField):
    alias = "type"
    default = "oci"
    help = "Artifact type (e.g., 'oci' for Docker images)."


class ArtifactUriField(StringField):
    alias = "uri"
    required = True
    help = "Artifact URI (e.g., 'registry.example.io/my-service:1.0.0')."


class ArtifactNameField(StringField):
    alias = "artifact_name"
    default = None
    help = "Artifact name."


class ArtifactDigestField(StringField):
    alias = "digest"
    default = None
    help = "Artifact digest (e.g., 'sha256:abc123...')."


# =============================================================================
# Target definitions
# =============================================================================


class SlsServiceTarget(Target):
    alias = "sls_service"
    help = softwrap(
        """
        A Python service packaged as an SLS distribution.

        Generates deployment/manifest.yml, service directory layout,
        init scripts, and Docker images following Palantir's Service
        Layout Specification.

        Example:

            sls_service(
                name="my-service",
                product_group="com.example",
                product_name="my-service",
                version="1.0.0",
                entrypoint="app:app",
                check_args=["--check"],
                product_dependencies=[":database-dep"],
            )
        """
    )
    core_fields = (
        *COMMON_TARGET_FIELDS,
        # Identity
        ProductGroupField,
        ProductNameField,
        VersionField,
        ProductTypeField,
        DisplayNameField,
        DescriptionField,
        # Python service config
        EntrypointField,
        CommandField,
        ServiceArgsField,
        PythonVersionField,
        EnvField,
        PexBinaryField,
        # Health checks
        CheckArgsField,
        CheckCommandField,
        CheckScriptField,
        # Resources
        ResourceRequestsField,
        ResourceLimitsField,
        ReplicationDesiredField,
        ReplicationMinField,
        ReplicationMaxField,
        # Metadata
        LabelsField,
        AnnotationsField,
        TraitsField,
        ManifestExtensionsField,
        # Dependencies
        ProductDependenciesField,
        ProductIncompatibilitiesField,
        ArtifactsField,
        # Sources
        SlsServiceSourcesField,
    )


class SlsProductDependencyTarget(Target):
    alias = "sls_product_dependency"
    help = softwrap(
        """
        Declares a product dependency following the SLS specification.

        Referenced by sls_service targets via the product_dependencies field.

        Example:

            sls_product_dependency(
                name="database-dep",
                product_group="com.example",
                product_name="sample-database",
                minimum_version="1.0.0",
                maximum_version="2.0.0",
            )
        """
    )
    core_fields = (
        *COMMON_TARGET_FIELDS,
        ProductGroupField,
        ProductNameField,
        MinimumVersionField,
        MaximumVersionField,
        RecommendedVersionField,
        OptionalField,
    )


class SlsProductIncompatibilityTarget(Target):
    alias = "sls_product_incompatibility"
    help = softwrap(
        """
        Declares a product incompatibility.

        Example:

            sls_product_incompatibility(
                name="legacy-incompat",
                product_group="com.example",
                product_name="legacy-service",
                version_range="< 2.0.0",
                reason="Incompatible API",
            )
        """
    )
    core_fields = (
        *COMMON_TARGET_FIELDS,
        ProductGroupField,
        ProductNameField,
        VersionRangeField,
        ReasonField,
    )


class SlsArtifactTarget(Target):
    alias = "sls_artifact"
    help = softwrap(
        """
        An artifact reference (OCI image, Helm chart, etc.)
        included in the manifest extensions.

        Example:

            sls_artifact(
                name="docker-image",
                type="oci",
                uri="registry.example.io/my-service:1.0.0",
            )
        """
    )
    core_fields = (
        *COMMON_TARGET_FIELDS,
        ArtifactTypeField,
        ArtifactUriField,
        ArtifactNameField,
        ArtifactDigestField,
    )


# =============================================================================
# Asset distribution fields
# =============================================================================


class AssetsField(DictStringToStringField):
    alias = "assets"
    help = softwrap(
        """
        Mapping of source paths to destination paths in the asset/ directory.
        Keys are source paths (relative to BUILD file), values are destination
        paths under asset/ in the distribution.

        Example: {'static/': 'web/static/', 'config/': 'conf/'}
        """
    )


class SlsAssetSourcesField(MultipleSourcesField):
    default = ("**/*",)
    help = "Files to include in the asset distribution."


# =============================================================================
# Asset distribution target
# =============================================================================


class SlsAssetTarget(Target):
    alias = "sls_asset"
    help = softwrap(
        """
        A static file distribution packaged as an SLS asset (product-type: asset.v1).

        Unlike sls_service, asset distributions have no runtime, no init script,
        and no health checks. They contain only deployment/manifest.yml and an
        asset/ directory with the packaged files.

        Example:

            sls_asset(
                name="frontend-assets",
                product_group="com.example",
                product_name="frontend-assets",
                version="1.0.0",
                assets={
                    "static/": "web/static/",
                    "config/": "conf/",
                },
            )
        """
    )
    core_fields = (
        *COMMON_TARGET_FIELDS,
        # Identity
        ProductGroupField,
        ProductNameField,
        VersionField,
        ProductTypeField,
        DisplayNameField,
        DescriptionField,
        # Assets
        AssetsField,
        # Dependencies
        ProductDependenciesField,
        ProductIncompatibilitiesField,
        ArtifactsField,
        # Metadata
        LabelsField,
        AnnotationsField,
        ManifestExtensionsField,
        # Sources
        SlsAssetSourcesField,
    )
