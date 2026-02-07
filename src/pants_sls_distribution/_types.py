"""Domain types for SLS distribution packaging."""

import re
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Optional

from pants.util.frozendict import FrozenDict


class ProductType(str, Enum):
    """SLS product types supported by the plugin."""

    HELM_V1 = "helm.v1"
    ASSET_V1 = "asset.v1"
    SERVICE_V1 = "service.v1"


# SLS orderable version patterns.
# Matches: 1.0.0, 1.0.0-rc1, 1.0.0-5-gabcdef, 1.0.0-rc1-5-gabcdef
ORDERABLE_VERSION_PATTERNS = [
    re.compile(r"^[0-9]+\.[0-9]+\.[0-9]+$"),
    re.compile(r"^[0-9]+\.[0-9]+\.[0-9]+-rc[0-9]+$"),
    re.compile(r"^[0-9]+\.[0-9]+\.[0-9]+-[0-9]+-g[a-f0-9]+$"),
    re.compile(r"^[0-9]+\.[0-9]+\.[0-9]+-rc[0-9]+-[0-9]+-g[a-f0-9]+$"),
]

# Maven-style product group: lowercase letters, digits, dots, hyphens.
PRODUCT_GROUP_PATTERN = re.compile(r"^[a-z0-9.-]+$")

# Product name: starts with lowercase letter, then lowercase letters, digits, dots, hyphens.
PRODUCT_NAME_PATTERN = re.compile(r"^[a-z][a-z0-9.-]*$")

# Version matcher for maximum-version (allows x wildcards).
VERSION_MATCHER_PATTERN = re.compile(
    r"^[0-9x]+\.[0-9x]+\.[0-9x]+$"
    r"|^[0-9]+\.[0-9]+\.[0-9]+$"
)


def is_orderable_version(version: str) -> bool:
    """Check if a version string matches any SLS orderable version pattern."""
    return any(p.match(version) for p in ORDERABLE_VERSION_PATTERNS)


def is_valid_product_group(group: str) -> bool:
    return bool(PRODUCT_GROUP_PATTERN.match(group))


def is_valid_product_name(name: str) -> bool:
    return bool(PRODUCT_NAME_PATTERN.match(name))


@dataclass(frozen=True)
class ProductDependency:
    """A resolved product dependency for manifest generation."""

    product_group: str
    product_name: str
    minimum_version: str
    maximum_version: Optional[str] = None
    recommended_version: Optional[str] = None
    optional: bool = False

    @property
    def product_id(self) -> str:
        return f"{self.product_group}:{self.product_name}"

    def to_manifest_dict(self) -> dict[str, Any]:
        """Serialize to the SLS manifest extensions format."""
        result: dict[str, Any] = {
            "product-group": self.product_group,
            "product-name": self.product_name,
            "minimum-version": self.minimum_version,
        }
        if self.maximum_version is not None:
            result["maximum-version"] = self.maximum_version
        if self.recommended_version is not None:
            result["recommended-version"] = self.recommended_version
        result["optional"] = self.optional
        return result


@dataclass(frozen=True)
class ProductIncompatibility:
    """A product incompatibility declaration."""

    product_group: str
    product_name: str
    version_range: str
    reason: str

    def to_manifest_dict(self) -> dict[str, Any]:
        return {
            "product-group": self.product_group,
            "product-name": self.product_name,
            "version-range": self.version_range,
            "reason": self.reason,
        }


@dataclass(frozen=True)
class Artifact:
    """An artifact reference (OCI image, etc.)."""

    type: str
    uri: str
    name: Optional[str] = None
    digest: Optional[str] = None

    def to_manifest_dict(self) -> dict[str, Any]:
        result: dict[str, Any] = {"type": self.type, "uri": self.uri}
        if self.name is not None:
            result["name"] = self.name
        if self.digest is not None:
            result["digest"] = self.digest
        return result


@dataclass(frozen=True)
class ManifestData:
    """Complete manifest data ready for YAML serialization."""

    manifest_version: str
    product_type: str
    product_group: str
    product_name: str
    product_version: str
    display_name: Optional[str] = None
    description: Optional[str] = None
    traits: tuple[str, ...] = ()
    labels: FrozenDict[str, str] = FrozenDict()
    annotations: FrozenDict[str, str] = FrozenDict()
    resource_requests: FrozenDict[str, str] = FrozenDict()
    resource_limits: FrozenDict[str, str] = FrozenDict()
    replication: FrozenDict[str, int] = FrozenDict()
    endpoints: tuple[FrozenDict[str, Any], ...] = ()
    volumes: tuple[FrozenDict[str, Any], ...] = ()
    secrets: tuple[FrozenDict[str, Any], ...] = ()
    product_dependencies: tuple[ProductDependency, ...] = ()
    product_incompatibilities: tuple[ProductIncompatibility, ...] = ()
    artifacts: tuple[Artifact, ...] = ()
    extensions: FrozenDict[str, Any] = FrozenDict()

    @property
    def product_id(self) -> str:
        return f"{self.product_group}:{self.product_name}"

    def to_dict(self) -> dict[str, Any]:
        """Serialize to the manifest YAML structure."""
        manifest: dict[str, Any] = {
            "manifest-version": self.manifest_version,
            "product-type": self.product_type,
            "product-group": self.product_group,
            "product-name": self.product_name,
            "product-version": self.product_version,
        }

        if self.display_name:
            manifest["display-name"] = self.display_name
        if self.description:
            manifest["description"] = self.description
        if self.traits:
            manifest["traits"] = list(self.traits)
        if self.labels:
            manifest["labels"] = dict(self.labels)
        if self.annotations:
            manifest["annotations"] = dict(self.annotations)

        if self.resource_requests or self.resource_limits:
            resources: dict[str, Any] = {}
            if self.resource_requests:
                resources["requests"] = dict(self.resource_requests)
            if self.resource_limits:
                resources["limits"] = dict(self.resource_limits)
            manifest["resources"] = resources

        if self.replication:
            manifest["replication"] = dict(self.replication)

        if self.endpoints:
            manifest["endpoints"] = [dict(e) for e in self.endpoints]
        if self.volumes:
            manifest["volumes"] = [dict(v) for v in self.volumes]
        if self.secrets:
            manifest["secrets"] = [dict(s) for s in self.secrets]

        # Build extensions
        extensions = dict(self.extensions)

        if self.product_dependencies:
            extensions["product-dependencies"] = [
                dep.to_manifest_dict() for dep in self.product_dependencies
            ]

        if self.product_incompatibilities:
            extensions["product-incompatibilities"] = [
                inc.to_manifest_dict() for inc in self.product_incompatibilities
            ]

        if self.artifacts:
            extensions["artifacts"] = [
                art.to_manifest_dict() for art in self.artifacts
            ]

        if extensions:
            manifest["extensions"] = extensions

        return manifest
