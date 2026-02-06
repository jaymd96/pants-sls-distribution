"""Tests for manifest validation logic (pure functions, no Pants engine)."""

from __future__ import annotations

import pytest

from pants_sls_distribution._types import (
    ManifestData,
    ProductDependency,
    ProductIncompatibility,
)
from pants_sls_distribution._validation import (
    resolve_default_max_version,
    validate_dependency,
    validate_manifest_data,
    validate_manifest_identity,
    validate_replication,
)
from pants_sls_distribution._exceptions import ManifestValidationError


class TestValidateManifestIdentity:
    def test_valid(self):
        validate_manifest_identity("com.example", "my-service", "1.0.0")

    def test_invalid_group(self):
        with pytest.raises(ManifestValidationError, match="product group"):
            validate_manifest_identity("Com.Example", "my-service", "1.0.0")

    def test_invalid_name(self):
        with pytest.raises(ManifestValidationError, match="product name"):
            validate_manifest_identity("com.example", "My-Service", "1.0.0")

    def test_invalid_version(self):
        with pytest.raises(ManifestValidationError, match="SLS version"):
            validate_manifest_identity("com.example", "my-service", "v1.0.0")


class TestValidateDependency:
    def test_valid_dependency(self):
        dep = ProductDependency(
            product_group="com.example",
            product_name="database",
            minimum_version="1.0.0",
            maximum_version="2.0.0",
        )
        validate_dependency(dep)

    def test_valid_dependency_with_wildcard_max(self):
        dep = ProductDependency(
            product_group="com.example",
            product_name="database",
            minimum_version="1.0.0",
            maximum_version="1.x.x",
        )
        validate_dependency(dep)

    def test_invalid_product_group(self):
        dep = ProductDependency(
            product_group="Com.Example",
            product_name="database",
            minimum_version="1.0.0",
        )
        with pytest.raises(ManifestValidationError, match="product group"):
            validate_dependency(dep)

    def test_invalid_product_name(self):
        dep = ProductDependency(
            product_group="com.example",
            product_name="Database",
            minimum_version="1.0.0",
        )
        with pytest.raises(ManifestValidationError, match="product name"):
            validate_dependency(dep)

    def test_invalid_minimum_version(self):
        dep = ProductDependency(
            product_group="com.example",
            product_name="database",
            minimum_version="latest",
        )
        with pytest.raises(ManifestValidationError, match="minimum version"):
            validate_dependency(dep)

    def test_lockstep_version_rejected(self):
        dep = ProductDependency(
            product_group="com.example",
            product_name="database",
            minimum_version="1.0.0",
            maximum_version="1.0.0",
        )
        with pytest.raises(ManifestValidationError, match="lockstep"):
            validate_dependency(dep)

    def test_invalid_recommended_version(self):
        dep = ProductDependency(
            product_group="com.example",
            product_name="database",
            minimum_version="1.0.0",
            recommended_version="latest",
        )
        with pytest.raises(ManifestValidationError, match="recommended version"):
            validate_dependency(dep)


class TestValidateReplication:
    def test_valid_replication(self):
        validate_replication({"desired": 2, "min": 1, "max": 5})

    def test_single_value(self):
        validate_replication({"desired": 3})

    def test_min_greater_than_desired(self):
        with pytest.raises(ManifestValidationError, match="min.*desired"):
            validate_replication({"desired": 1, "min": 3, "max": 5})

    def test_desired_greater_than_max(self):
        with pytest.raises(ManifestValidationError, match="desired.*max"):
            validate_replication({"desired": 10, "min": 1, "max": 5})

    def test_min_greater_than_max(self):
        with pytest.raises(ManifestValidationError, match="min.*max"):
            validate_replication({"min": 5, "max": 2})


class TestResolveDefaultMaxVersion:
    def test_major_1(self):
        assert resolve_default_max_version("1.0.0") == "1.x.x"

    def test_major_2(self):
        assert resolve_default_max_version("2.5.3") == "2.x.x"

    def test_major_0(self):
        assert resolve_default_max_version("0.1.0") == "0.x.x"


class TestValidateManifestData:
    def test_valid_manifest(self):
        data = ManifestData(
            manifest_version="1.0",
            product_type="helm.v1",
            product_group="com.example",
            product_name="my-service",
            product_version="1.0.0",
        )
        errors, warnings = validate_manifest_data(data)
        assert errors == []
        assert warnings == []

    def test_missing_required_fields(self):
        data = ManifestData(
            manifest_version="1.0",
            product_type="",
            product_group="",
            product_name="",
            product_version="",
        )
        errors, warnings = validate_manifest_data(data)
        assert len(errors) >= 4

    def test_invalid_product_type(self):
        data = ManifestData(
            manifest_version="1.0",
            product_type="invalid.v1",
            product_group="com.example",
            product_name="my-service",
            product_version="1.0.0",
        )
        errors, _ = validate_manifest_data(data)
        assert any("product-type" in e for e in errors)

    def test_duplicate_dependency(self):
        dep = ProductDependency(
            product_group="com.example",
            product_name="database",
            minimum_version="1.0.0",
        )
        data = ManifestData(
            manifest_version="1.0",
            product_type="helm.v1",
            product_group="com.example",
            product_name="my-service",
            product_version="1.0.0",
            product_dependencies=(dep, dep),
        )
        errors, _ = validate_manifest_data(data)
        assert any("Duplicate" in e for e in errors)

    def test_lockstep_dependency_detected(self):
        dep = ProductDependency(
            product_group="com.example",
            product_name="database",
            minimum_version="1.0.0",
            maximum_version="1.0.0",
        )
        data = ManifestData(
            manifest_version="1.0",
            product_type="helm.v1",
            product_group="com.example",
            product_name="my-service",
            product_version="1.0.0",
            product_dependencies=(dep,),
        )
        errors, _ = validate_manifest_data(data)
        assert any("lockstep" in e for e in errors)

    def test_incompatibility_without_reason_warns(self):
        data = ManifestData(
            manifest_version="1.0",
            product_type="helm.v1",
            product_group="com.example",
            product_name="my-service",
            product_version="1.0.0",
            product_incompatibilities=(
                ProductIncompatibility(
                    product_group="com.example",
                    product_name="legacy",
                    version_range="< 2.0.0",
                    reason="",
                ),
            ),
        )
        errors, warnings = validate_manifest_data(data)
        assert any("no reason" in w for w in warnings)

    def test_invalid_replication(self):
        data = ManifestData(
            manifest_version="1.0",
            product_type="helm.v1",
            product_group="com.example",
            product_name="my-service",
            product_version="1.0.0",
            replication={"desired": 10, "min": 1, "max": 5},
        )
        errors, _ = validate_manifest_data(data)
        assert any("desired" in e and "max" in e for e in errors)


class TestManifestDataToYaml:
    """Test that ManifestData serializes correctly for the SLS spec."""

    def test_manifest_with_dependencies(self):
        data = ManifestData(
            manifest_version="1.0",
            product_type="helm.v1",
            product_group="com.example",
            product_name="sample-service",
            product_version="1.0.0",
            product_dependencies=(
                ProductDependency(
                    product_group="com.example",
                    product_name="sample-database",
                    minimum_version="1.0.0",
                    maximum_version="2.0.0",
                    recommended_version="1.2.0",
                    optional=False,
                ),
                ProductDependency(
                    product_group="com.example",
                    product_name="sample-cache",
                    minimum_version="3.0.0",
                    optional=True,
                ),
            ),
        )
        result = data.to_dict()
        deps = result["extensions"]["product-dependencies"]

        assert len(deps) == 2
        assert deps[0]["product-group"] == "com.example"
        assert deps[0]["product-name"] == "sample-database"
        assert deps[0]["minimum-version"] == "1.0.0"
        assert deps[0]["maximum-version"] == "2.0.0"
        assert deps[0]["recommended-version"] == "1.2.0"
        assert deps[0]["optional"] is False
        assert deps[1]["optional"] is True

    def test_manifest_yaml_roundtrip(self):
        """Verify the manifest can be serialized to YAML and parsed back."""
        import yaml

        data = ManifestData(
            manifest_version="1.0",
            product_type="helm.v1",
            product_group="com.example",
            product_name="roundtrip-service",
            product_version="2.1.0",
            display_name="Roundtrip Service",
            labels={"team": "platform"},
            resource_requests={"cpu": "100m", "memory": "128Mi"},
        )

        yaml_str = yaml.dump(data.to_dict(), default_flow_style=False, sort_keys=False)
        parsed = yaml.safe_load(yaml_str)

        assert parsed["manifest-version"] == "1.0"
        assert parsed["product-type"] == "helm.v1"
        assert parsed["product-group"] == "com.example"
        assert parsed["product-name"] == "roundtrip-service"
        assert parsed["product-version"] == "2.1.0"
        assert parsed["display-name"] == "Roundtrip Service"
        assert parsed["labels"]["team"] == "platform"
        assert parsed["resources"]["requests"]["cpu"] == "100m"
