"""Exception hierarchy for SLS distribution plugin."""

from __future__ import annotations


class SlsDistributionError(Exception):
    """Base for all SLS distribution plugin errors."""


class ManifestValidationError(SlsDistributionError):
    """Manifest failed schema or semantic validation."""

    def __init__(self, message: str, *, field: str | None = None):
        self.field = field
        prefix = f"[{field}] " if field else ""
        super().__init__(f"{prefix}{message}")


class VersionFormatError(SlsDistributionError):
    """Version string does not match SLS orderable format."""

    def __init__(self, version: str):
        self.version = version
        super().__init__(
            f"Invalid SLS version: {version!r}. "
            "Must match X.Y.Z, X.Y.Z-rcN, X.Y.Z-N-gHASH, or X.Y.Z-rcN-N-gHASH"
        )


class DependencyValidationError(SlsDistributionError):
    """Product dependency failed validation."""

    def __init__(self, product_id: str, message: str):
        self.product_id = product_id
        super().__init__(f"Dependency {product_id}: {message}")
