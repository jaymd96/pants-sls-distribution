"""Pure Python lock file generation and parsing (no Pants dependencies).

Generates and parses ``product-dependencies.lock`` files.

Format::

    # product-dependencies.lock
    # Run pants sls-lock to regenerate this file
    com.example:auth-service (1.2.0, 1.x.x)
    com.example:storage-service (3.56.0, 3.x.x)
    com.example:email-service (1.200.3, 2.x.x) optional
"""

import re
from dataclasses import dataclass
from typing import List, Sequence, Tuple, Union

from pants_sls_distribution._types import ProductDependency
from pants_sls_distribution._validation import resolve_default_max_version

_LOCK_HEADER = (
    "# product-dependencies.lock\n"
    "# Run pants sls-lock to regenerate this file\n"
)

# Parse: group:name (min, max)[ optional]
_LOCK_LINE_PATTERN = re.compile(
    r"^(?P<group>[a-z0-9.-]+):(?P<name>[a-z][a-z0-9.-]*)"
    r"\s+\((?P<min>[^,]+),\s*(?P<max>[^)]+)\)"
    r"(?:\s+(?P<optional>optional))?\s*$"
)


@dataclass(frozen=True)
class LockEntry:
    """A single entry in a product-dependencies.lock file."""

    product_group: str
    product_name: str
    minimum_version: str
    maximum_version: str
    optional: bool = False

    @property
    def product_id(self) -> str:
        return f"{self.product_group}:{self.product_name}"

    def to_line(self) -> str:
        """Serialize to a single lock file line."""
        suffix = " optional" if self.optional else ""
        return f"{self.product_id} ({self.minimum_version}, {self.maximum_version}){suffix}"


def generate_lock_file(dependencies: Union[Tuple[ProductDependency, ...], List[ProductDependency]]) -> str:
    """Generate lock file content from product dependencies.

    Dependencies are sorted by product_id for deterministic output.

    Args:
        dependencies: Product dependencies to include.

    Returns:
        Complete lock file content as a string.
    """
    entries = []
    for dep in dependencies:
        max_version = dep.maximum_version
        if max_version is None:
            max_version = resolve_default_max_version(dep.minimum_version)

        entries.append(LockEntry(
            product_group=dep.product_group,
            product_name=dep.product_name,
            minimum_version=dep.minimum_version,
            maximum_version=max_version,
            optional=dep.optional,
        ))

    # Sort for deterministic output
    entries.sort(key=lambda e: e.product_id)

    lines = [_LOCK_HEADER]
    for entry in entries:
        lines.append(entry.to_line())

    # Trailing newline
    return "\n".join(lines) + "\n"


def parse_lock_file(content: str) -> list[LockEntry]:
    """Parse lock file content into LockEntry list.

    Args:
        content: Lock file content string.

    Returns:
        List of LockEntry objects.

    Raises:
        ValueError: If a non-comment, non-empty line doesn't match the format.
    """
    entries = []
    for line_num, line in enumerate(content.splitlines(), start=1):
        stripped = line.strip()
        if not stripped or stripped.startswith("#"):
            continue

        match = _LOCK_LINE_PATTERN.match(stripped)
        if not match:
            raise ValueError(
                f"Invalid lock file line {line_num}: {line!r}"
            )

        entries.append(LockEntry(
            product_group=match.group("group"),
            product_name=match.group("name"),
            minimum_version=match.group("min").strip(),
            maximum_version=match.group("max").strip(),
            optional=match.group("optional") is not None,
        ))

    return entries


def validate_lock_file(content: str) -> list[str]:
    """Validate lock file content and return any errors.

    Checks:
      - All lines parse correctly
      - No duplicate product IDs
      - Versions are non-empty

    Returns:
        List of error messages (empty if valid).
    """
    errors: list[str] = []

    try:
        entries = parse_lock_file(content)
    except ValueError as exc:
        return [str(exc)]

    seen: set[str] = set()
    for entry in entries:
        if entry.product_id in seen:
            errors.append(f"Duplicate dependency in lock file: {entry.product_id}")
        seen.add(entry.product_id)

        if not entry.minimum_version:
            errors.append(f"{entry.product_id}: empty minimum_version")
        if not entry.maximum_version:
            errors.append(f"{entry.product_id}: empty maximum_version")

    return errors
