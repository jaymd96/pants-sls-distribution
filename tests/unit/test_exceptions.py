"""Tests for SLS distribution exceptions."""

from __future__ import annotations

from pants_sls_distribution._exceptions import (
    DependencyValidationError,
    ManifestValidationError,
    SlsDistributionError,
    VersionFormatError,
)


class TestExceptionHierarchy:
    def test_base_exception(self):
        assert issubclass(ManifestValidationError, SlsDistributionError)
        assert issubclass(VersionFormatError, SlsDistributionError)
        assert issubclass(DependencyValidationError, SlsDistributionError)


class TestManifestValidationError:
    def test_without_field(self):
        err = ManifestValidationError("bad value")
        assert str(err) == "bad value"
        assert err.field is None

    def test_with_field(self):
        err = ManifestValidationError("bad value", field="product-name")
        assert str(err) == "[product-name] bad value"
        assert err.field == "product-name"


class TestVersionFormatError:
    def test_message(self):
        err = VersionFormatError("abc")
        assert "abc" in str(err)
        assert err.version == "abc"


class TestDependencyValidationError:
    def test_message(self):
        err = DependencyValidationError("com.example:db", "version too low")
        assert "com.example:db" in str(err)
        assert "version too low" in str(err)
        assert err.product_id == "com.example:db"
