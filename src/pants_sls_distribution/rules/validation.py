"""Manifest validation rule: validate manifest against JSON schema and semantic rules."""

import json
import logging
from dataclasses import dataclass
from importlib import resources as importlib_resources
from typing import Any, Optional

from pants.engine.rules import Get, collect_rules, rule

from pants_sls_distribution._types import ManifestData
from pants_sls_distribution._validation import validate_manifest_data
from pants_sls_distribution.rules.manifest import SlsManifest, SlsManifestRequest
from pants_sls_distribution.subsystem import SlsDistributionSubsystem

logger = logging.getLogger(__name__)


# =============================================================================
# Request / Result types
# =============================================================================


@dataclass(frozen=True)
class SlsValidationRequest:
    """Request to validate a manifest."""

    manifest: SlsManifest


@dataclass(frozen=True)
class SlsValidationResult:
    """Result of manifest validation."""

    valid: bool
    errors: tuple[str, ...]
    warnings: tuple[str, ...]

    @classmethod
    def success(cls, *, warnings: tuple[str, ...] = ()) -> "SlsValidationResult":
        return cls(valid=True, errors=(), warnings=warnings)

    @classmethod
    def failure(cls, errors: tuple[str, ...], *, warnings: tuple[str, ...] = ()) -> "SlsValidationResult":
        return cls(valid=False, errors=errors, warnings=warnings)


# =============================================================================
# Schema loading
# =============================================================================

_SCHEMA_CACHE: Optional[dict[str, Any]] = None


def _load_manifest_schema() -> dict[str, Any]:
    """Load the manifest.v1.json schema from bundled resources."""
    global _SCHEMA_CACHE
    if _SCHEMA_CACHE is not None:
        return _SCHEMA_CACHE

    schema_path = (
        importlib_resources.files("pants_sls_distribution")
        / "schemas"
        / "manifest.v1.json"
    )
    _SCHEMA_CACHE = json.loads(schema_path.read_text(encoding="utf-8"))
    return _SCHEMA_CACHE


# =============================================================================
# Rules
# =============================================================================


@rule(desc="Validate SLS manifest")
async def validate_manifest(
    request: SlsValidationRequest,
    subsystem: SlsDistributionSubsystem,
) -> SlsValidationResult:
    manifest = request.manifest
    data = manifest.data

    # Use the pure validation function for all semantic checks
    errors_list, warnings_list = validate_manifest_data(data)
    errors = list(errors_list)
    warnings = list(warnings_list)

    # --- JSON Schema validation (optional, requires jsonschema) ---
    if subsystem.strict_validation:
        schema_errors, schema_warnings = _validate_against_schema(data)
        errors.extend(schema_errors)
        warnings.extend(schema_warnings)

    if errors:
        return SlsValidationResult.failure(tuple(errors), warnings=tuple(warnings))

    logger.info("Manifest validation passed for %s", manifest.product_id)
    return SlsValidationResult.success(warnings=tuple(warnings))


def _validate_against_schema(data: ManifestData) -> tuple[list[str], list[str]]:
    """Validate manifest dict against the JSON schema. Returns (errors, warnings)."""
    try:
        import jsonschema
    except ImportError:
        return [], ["jsonschema package not available; skipping schema validation"]

    schema = _load_manifest_schema()
    manifest_dict = data.to_dict()

    validator = jsonschema.Draft7Validator(schema)
    errors = []
    for error in validator.iter_errors(manifest_dict):
        path = ".".join(str(p) for p in error.absolute_path)
        prefix = f"[{path}] " if path else ""
        errors.append(f"Schema: {prefix}{error.message}")
    return errors, []


def rules():
    return collect_rules()
