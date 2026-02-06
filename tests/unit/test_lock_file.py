"""Tests for lock file generation and parsing (pure functions, no Pants engine)."""

from __future__ import annotations

import pytest

from pants_sls_distribution._lock_file import (
    LockEntry,
    generate_lock_file,
    parse_lock_file,
    validate_lock_file,
)
from pants_sls_distribution._types import ProductDependency


# =============================================================================
# LockEntry
# =============================================================================


class TestLockEntry:
    """Test LockEntry dataclass."""

    def test_product_id(self):
        entry = LockEntry("com.example", "my-svc", "1.0.0", "1.x.x")
        assert entry.product_id == "com.example:my-svc"

    def test_to_line_required(self):
        entry = LockEntry("com.example", "auth-service", "1.2.0", "1.x.x")
        assert entry.to_line() == "com.example:auth-service (1.2.0, 1.x.x)"

    def test_to_line_optional(self):
        entry = LockEntry("com.example", "cache", "3.0.0", "3.x.x", optional=True)
        assert entry.to_line() == "com.example:cache (3.0.0, 3.x.x) optional"

    def test_frozen(self):
        entry = LockEntry("com.example", "svc", "1.0.0", "1.x.x")
        with pytest.raises(AttributeError):
            entry.product_group = "other"  # type: ignore[misc]


# =============================================================================
# generate_lock_file
# =============================================================================


class TestGenerateLockFile:
    """Test lock file generation from ProductDependency list."""

    def test_empty_dependencies(self):
        content = generate_lock_file(())
        assert "# product-dependencies.lock" in content
        assert "# Run pants sls-lock" in content
        # Only header, no dependency lines
        lines = [l for l in content.strip().splitlines() if l and not l.startswith("#")]
        assert lines == []

    def test_single_dependency(self):
        deps = (
            ProductDependency(
                product_group="com.example",
                product_name="auth-service",
                minimum_version="1.2.0",
                maximum_version="1.x.x",
            ),
        )
        content = generate_lock_file(deps)
        assert "com.example:auth-service (1.2.0, 1.x.x)" in content

    def test_multiple_dependencies_sorted(self):
        deps = (
            ProductDependency(
                product_group="com.example",
                product_name="zebra-service",
                minimum_version="2.0.0",
                maximum_version="2.x.x",
            ),
            ProductDependency(
                product_group="com.example",
                product_name="alpha-service",
                minimum_version="1.0.0",
                maximum_version="1.x.x",
            ),
        )
        content = generate_lock_file(deps)
        lines = [l for l in content.strip().splitlines() if l and not l.startswith("#")]
        assert len(lines) == 2
        # Alphabetically sorted
        assert "alpha-service" in lines[0]
        assert "zebra-service" in lines[1]

    def test_optional_dependency(self):
        deps = (
            ProductDependency(
                product_group="com.example",
                product_name="cache",
                minimum_version="3.0.0",
                maximum_version="3.x.x",
                optional=True,
            ),
        )
        content = generate_lock_file(deps)
        assert "com.example:cache (3.0.0, 3.x.x) optional" in content

    def test_default_max_version_derived(self):
        deps = (
            ProductDependency(
                product_group="com.example",
                product_name="database",
                minimum_version="5.3.0",
                # No maximum_version -> should derive 5.x.x
            ),
        )
        content = generate_lock_file(deps)
        assert "com.example:database (5.3.0, 5.x.x)" in content

    def test_explicit_max_version_preserved(self):
        deps = (
            ProductDependency(
                product_group="com.example",
                product_name="database",
                minimum_version="5.3.0",
                maximum_version="6.0.0",
            ),
        )
        content = generate_lock_file(deps)
        assert "com.example:database (5.3.0, 6.0.0)" in content

    def test_trailing_newline(self):
        content = generate_lock_file(())
        assert content.endswith("\n")

    def test_header_present(self):
        content = generate_lock_file(())
        assert content.startswith("# product-dependencies.lock\n")


# =============================================================================
# parse_lock_file
# =============================================================================


class TestParseLockFile:
    """Test lock file parsing."""

    def test_parse_simple(self):
        content = (
            "# product-dependencies.lock\n"
            "com.example:auth-service (1.2.0, 1.x.x)\n"
        )
        entries = parse_lock_file(content)
        assert len(entries) == 1
        assert entries[0].product_group == "com.example"
        assert entries[0].product_name == "auth-service"
        assert entries[0].minimum_version == "1.2.0"
        assert entries[0].maximum_version == "1.x.x"
        assert entries[0].optional is False

    def test_parse_optional(self):
        content = "com.example:cache (3.0.0, 3.x.x) optional\n"
        entries = parse_lock_file(content)
        assert len(entries) == 1
        assert entries[0].optional is True

    def test_parse_multiple(self):
        content = (
            "# header\n"
            "com.example:alpha (1.0.0, 1.x.x)\n"
            "com.example:beta (2.0.0, 2.x.x) optional\n"
            "com.example:gamma (3.0.0, 4.0.0)\n"
        )
        entries = parse_lock_file(content)
        assert len(entries) == 3
        assert entries[0].product_name == "alpha"
        assert entries[1].product_name == "beta"
        assert entries[1].optional is True
        assert entries[2].maximum_version == "4.0.0"

    def test_skips_empty_lines(self):
        content = "\n\ncom.example:svc (1.0.0, 1.x.x)\n\n"
        entries = parse_lock_file(content)
        assert len(entries) == 1

    def test_skips_comment_lines(self):
        content = (
            "# comment 1\n"
            "# comment 2\n"
            "com.example:svc (1.0.0, 1.x.x)\n"
        )
        entries = parse_lock_file(content)
        assert len(entries) == 1

    def test_invalid_line_raises(self):
        content = "this is not valid\n"
        with pytest.raises(ValueError, match="Invalid lock file line"):
            parse_lock_file(content)

    def test_invalid_line_number_in_error(self):
        content = "# header\ninvalid line here\n"
        with pytest.raises(ValueError, match="line 2"):
            parse_lock_file(content)


# =============================================================================
# Roundtrip
# =============================================================================


class TestLockFileRoundtrip:
    """Test generate -> parse roundtrip."""

    def test_roundtrip_single(self):
        deps = (
            ProductDependency(
                product_group="com.example",
                product_name="auth-service",
                minimum_version="1.2.0",
                maximum_version="1.x.x",
            ),
        )
        content = generate_lock_file(deps)
        entries = parse_lock_file(content)
        assert len(entries) == 1
        assert entries[0].product_group == "com.example"
        assert entries[0].product_name == "auth-service"
        assert entries[0].minimum_version == "1.2.0"
        assert entries[0].maximum_version == "1.x.x"

    def test_roundtrip_multiple_with_optional(self):
        deps = (
            ProductDependency("com.example", "alpha", "1.0.0", "1.x.x"),
            ProductDependency("com.example", "beta", "2.0.0", "2.x.x", optional=True),
            ProductDependency("com.other", "gamma", "3.1.0", "4.0.0"),
        )
        content = generate_lock_file(deps)
        entries = parse_lock_file(content)
        assert len(entries) == 3
        # Sorted by product_id
        assert entries[0].product_id == "com.example:alpha"
        assert entries[1].product_id == "com.example:beta"
        assert entries[1].optional is True
        assert entries[2].product_id == "com.other:gamma"

    def test_roundtrip_empty(self):
        content = generate_lock_file(())
        entries = parse_lock_file(content)
        assert entries == []


# =============================================================================
# validate_lock_file
# =============================================================================


class TestValidateLockFile:
    """Test lock file validation."""

    def test_valid_file(self):
        content = (
            "# header\n"
            "com.example:svc (1.0.0, 1.x.x)\n"
        )
        errors = validate_lock_file(content)
        assert errors == []

    def test_duplicate_dependency(self):
        content = (
            "com.example:svc (1.0.0, 1.x.x)\n"
            "com.example:svc (2.0.0, 2.x.x)\n"
        )
        errors = validate_lock_file(content)
        assert len(errors) == 1
        assert "Duplicate" in errors[0]

    def test_invalid_format(self):
        content = "not a valid line\n"
        errors = validate_lock_file(content)
        assert len(errors) == 1
        assert "Invalid" in errors[0]

    def test_empty_file_is_valid(self):
        content = "# just comments\n"
        errors = validate_lock_file(content)
        assert errors == []
