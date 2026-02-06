"""Pure validation functions (no Pants engine dependencies).

These are extracted so they can be tested without the Pants runtime.
The rules/manifest.py and rules/validation.py modules call into these.
"""

from __future__ import annotations

from pants_sls_distribution._exceptions import ManifestValidationError
from pants_sls_distribution._types import (
    ManifestData,
    ProductDependency,
    is_orderable_version,
    is_valid_product_group,
    is_valid_product_name,
)


def validate_dependency(dep: ProductDependency) -> None:
    """Validate product dependency semantics."""
    if not is_valid_product_group(dep.product_group):
        raise ManifestValidationError(
            f"Invalid product group in dependency: {dep.product_group!r}",
            field="product-dependencies",
        )

    if not is_valid_product_name(dep.product_name):
        raise ManifestValidationError(
            f"Invalid product name in dependency: {dep.product_name!r}",
            field="product-dependencies",
        )

    if not is_orderable_version(dep.minimum_version):
        raise ManifestValidationError(
            f"Invalid minimum version: {dep.minimum_version!r}",
            field="product-dependencies",
        )

    # minimum_version != maximum_version (prevents lockstep upgrade antipattern)
    if dep.maximum_version and dep.minimum_version == dep.maximum_version:
        raise ManifestValidationError(
            f"minimum_version must not equal maximum_version for {dep.product_id}. "
            "This creates a lockstep upgrade requirement.",
            field="product-dependencies",
        )

    # recommended_version must be a valid orderable version if set
    if dep.recommended_version and not is_orderable_version(dep.recommended_version):
        raise ManifestValidationError(
            f"Invalid recommended version: {dep.recommended_version!r}",
            field="product-dependencies",
        )


def validate_replication(replication: dict[str, int]) -> None:
    """Validate replication constraints: min <= desired <= max."""
    desired = replication.get("desired")
    min_val = replication.get("min")
    max_val = replication.get("max")

    if min_val is not None and desired is not None and min_val > desired:
        raise ManifestValidationError(
            f"replication.min ({min_val}) must be <= replication.desired ({desired})",
            field="replication",
        )
    if desired is not None and max_val is not None and desired > max_val:
        raise ManifestValidationError(
            f"replication.desired ({desired}) must be <= replication.max ({max_val})",
            field="replication",
        )
    if min_val is not None and max_val is not None and min_val > max_val:
        raise ManifestValidationError(
            f"replication.min ({min_val}) must be <= replication.max ({max_val})",
            field="replication",
        )


def validate_manifest_identity(
    product_group: str,
    product_name: str,
    version: str,
) -> None:
    """Validate manifest identity fields."""
    if not is_valid_product_group(product_group):
        raise ManifestValidationError(
            f"Invalid product group: {product_group!r}. "
            "Must be lowercase letters, digits, dots, and hyphens.",
            field="product-group",
        )

    if not is_valid_product_name(product_name):
        raise ManifestValidationError(
            f"Invalid product name: {product_name!r}. "
            "Must start with lowercase letter; allows lowercase letters, digits, dots, hyphens.",
            field="product-name",
        )

    if not is_orderable_version(version):
        raise ManifestValidationError(
            f"Invalid SLS version: {version!r}. "
            "Must match X.Y.Z, X.Y.Z-rcN, X.Y.Z-N-gHASH, or X.Y.Z-rcN-N-gHASH",
            field="product-version",
        )


def resolve_default_max_version(minimum_version: str) -> str:
    """Derive default maximum version as '<major>.x.x' from minimum_version."""
    major = minimum_version.split(".")[0]
    return f"{major}.x.x"


def validate_manifest_data(data: ManifestData) -> tuple[list[str], list[str]]:
    """Validate a complete ManifestData. Returns (errors, warnings)."""
    errors: list[str] = []
    warnings: list[str] = []

    # Required fields
    if not data.product_group:
        errors.append("product-group is required")
    if not data.product_name:
        errors.append("product-name is required")
    if not data.product_version:
        errors.append("product-version is required")
    if not data.product_type:
        errors.append("product-type is required")

    # Version format
    if data.product_version and not is_orderable_version(data.product_version):
        errors.append(
            f"product-version {data.product_version!r} is not a valid SLS orderable version"
        )

    # Product type
    valid_types = {"helm.v1", "asset.v1", "service.v1"}
    if data.product_type and data.product_type not in valid_types:
        errors.append(f"product-type {data.product_type!r} not in {valid_types}")

    # Replication semantics
    if data.replication:
        desired = data.replication.get("desired")
        min_val = data.replication.get("min")
        max_val = data.replication.get("max")
        if min_val is not None and desired is not None and min_val > desired:
            errors.append(f"replication.min ({min_val}) > replication.desired ({desired})")
        if desired is not None and max_val is not None and desired > max_val:
            errors.append(f"replication.desired ({desired}) > replication.max ({max_val})")

    # Dependency validation
    seen_dep_ids: set[str] = set()
    for dep in data.product_dependencies:
        dep_id = dep.product_id
        if dep_id in seen_dep_ids:
            errors.append(f"Duplicate product dependency: {dep_id}")
        seen_dep_ids.add(dep_id)

        if not is_orderable_version(dep.minimum_version):
            errors.append(f"Dependency {dep_id}: invalid minimum_version {dep.minimum_version!r}")

        if dep.minimum_version == dep.maximum_version:
            errors.append(
                f"Dependency {dep_id}: minimum_version == maximum_version "
                f"({dep.minimum_version}). This creates lockstep upgrade coupling."
            )

        if dep.recommended_version and not is_orderable_version(dep.recommended_version):
            errors.append(
                f"Dependency {dep_id}: invalid recommended_version {dep.recommended_version!r}"
            )

    # Incompatibility warnings
    for incompat in data.product_incompatibilities:
        if not incompat.reason:
            warnings.append(
                f"Incompatibility with {incompat.product_group}:{incompat.product_name} "
                "has no reason specified"
            )

    return errors, warnings
