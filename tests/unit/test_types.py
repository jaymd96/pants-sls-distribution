"""Tests for SLS distribution domain types."""

from __future__ import annotations

import pytest

from pants_sls_distribution._types import (
    Artifact,
    ManifestData,
    ProductDependency,
    ProductIncompatibility,
    is_orderable_version,
    is_valid_product_group,
    is_valid_product_name,
)


class TestIsOrderableVersion:
    """Test SLS orderable version pattern matching."""

    @pytest.mark.parametrize(
        "version",
        [
            "0.0.0",
            "1.0.0",
            "1.2.3",
            "10.20.30",
            "999.999.999",
        ],
    )
    def test_standard_versions(self, version: str):
        assert is_orderable_version(version)

    @pytest.mark.parametrize(
        "version",
        [
            "1.0.0-rc1",
            "1.2.3-rc42",
            "0.0.1-rc0",
        ],
    )
    def test_release_candidates(self, version: str):
        assert is_orderable_version(version)

    @pytest.mark.parametrize(
        "version",
        [
            "1.0.0-5-gabcdef",
            "1.2.3-1-g0000000",
            "0.0.1-100-gdeadbeef",
        ],
    )
    def test_git_snapshots(self, version: str):
        assert is_orderable_version(version)

    @pytest.mark.parametrize(
        "version",
        [
            "1.0.0-rc1-5-gabcdef",
            "1.2.3-rc2-1-g0000000",
        ],
    )
    def test_rc_git_snapshots(self, version: str):
        assert is_orderable_version(version)

    @pytest.mark.parametrize(
        "version",
        [
            "",
            "1",
            "1.0",
            "v1.0.0",
            "1.0.0-beta1",
            "1.0.0-SNAPSHOT",
            "1.0.0.0",
            "1.x.x",
            "latest",
            "1.0.0-rc",
            "1.0.0-0-gGGGGGGG",  # uppercase not allowed in hash
        ],
    )
    def test_invalid_versions(self, version: str):
        assert not is_orderable_version(version)


class TestIsValidProductGroup:
    @pytest.mark.parametrize(
        "group",
        ["com.example", "com.example.platform", "my-group", "a123"],
    )
    def test_valid_groups(self, group: str):
        assert is_valid_product_group(group)

    @pytest.mark.parametrize(
        "group",
        ["", "Com.Example", "com example", "com/example", "COM.EXAMPLE"],
    )
    def test_invalid_groups(self, group: str):
        assert not is_valid_product_group(group)


class TestIsValidProductName:
    @pytest.mark.parametrize(
        "name",
        ["my-service", "a", "my.service", "service-1.0"],
    )
    def test_valid_names(self, name: str):
        assert is_valid_product_name(name)

    @pytest.mark.parametrize(
        "name",
        ["", "1service", "-service", "My-Service", "my service"],
    )
    def test_invalid_names(self, name: str):
        assert not is_valid_product_name(name)


class TestProductDependency:
    def test_product_id(self):
        dep = ProductDependency(
            product_group="com.example",
            product_name="database",
            minimum_version="1.0.0",
        )
        assert dep.product_id == "com.example:database"

    def test_to_manifest_dict_minimal(self):
        dep = ProductDependency(
            product_group="com.example",
            product_name="database",
            minimum_version="1.0.0",
        )
        result = dep.to_manifest_dict()
        assert result == {
            "product-group": "com.example",
            "product-name": "database",
            "minimum-version": "1.0.0",
            "optional": False,
        }

    def test_to_manifest_dict_full(self):
        dep = ProductDependency(
            product_group="com.example",
            product_name="database",
            minimum_version="1.0.0",
            maximum_version="2.0.0",
            recommended_version="1.2.0",
            optional=True,
        )
        result = dep.to_manifest_dict()
        assert result == {
            "product-group": "com.example",
            "product-name": "database",
            "minimum-version": "1.0.0",
            "maximum-version": "2.0.0",
            "recommended-version": "1.2.0",
            "optional": True,
        }


class TestManifestData:
    def test_minimal_manifest(self):
        data = ManifestData(
            manifest_version="1.0",
            product_type="helm.v1",
            product_group="com.example",
            product_name="my-service",
            product_version="1.0.0",
        )
        result = data.to_dict()
        assert result == {
            "manifest-version": "1.0",
            "product-type": "helm.v1",
            "product-group": "com.example",
            "product-name": "my-service",
            "product-version": "1.0.0",
        }

    def test_product_id(self):
        data = ManifestData(
            manifest_version="1.0",
            product_type="helm.v1",
            product_group="com.example",
            product_name="my-service",
            product_version="1.0.0",
        )
        assert data.product_id == "com.example:my-service"

    def test_full_manifest(self):
        data = ManifestData(
            manifest_version="1.0",
            product_type="helm.v1",
            product_group="com.example",
            product_name="my-service",
            product_version="1.0.0",
            display_name="My Service",
            description="A test service",
            traits=("api", "web"),
            labels={"team": "platform"},
            annotations={"docs": "https://example.com"},
            resource_requests={"cpu": "100m", "memory": "128Mi"},
            resource_limits={"cpu": "500m", "memory": "512Mi"},
            replication={"desired": 2, "min": 1, "max": 5},
            product_dependencies=(
                ProductDependency(
                    product_group="com.example",
                    product_name="database",
                    minimum_version="1.0.0",
                    maximum_version="2.0.0",
                ),
            ),
            artifacts=(
                Artifact(type="oci", uri="registry.example.io/my-service:1.0.0"),
            ),
        )
        result = data.to_dict()

        assert result["display-name"] == "My Service"
        assert result["description"] == "A test service"
        assert result["traits"] == ["api", "web"]
        assert result["labels"] == {"team": "platform"}
        assert result["resources"]["requests"]["cpu"] == "100m"
        assert result["resources"]["limits"]["memory"] == "512Mi"
        assert result["replication"]["desired"] == 2
        assert len(result["extensions"]["product-dependencies"]) == 1
        assert result["extensions"]["product-dependencies"][0]["product-name"] == "database"
        assert len(result["extensions"]["artifacts"]) == 1

    def test_extensions_not_included_when_empty(self):
        data = ManifestData(
            manifest_version="1.0",
            product_type="helm.v1",
            product_group="com.example",
            product_name="my-service",
            product_version="1.0.0",
        )
        result = data.to_dict()
        assert "extensions" not in result

    def test_custom_extensions_merged(self):
        data = ManifestData(
            manifest_version="1.0",
            product_type="helm.v1",
            product_group="com.example",
            product_name="my-service",
            product_version="1.0.0",
            extensions={"require-stable-hostname": False},
            product_dependencies=(
                ProductDependency(
                    product_group="com.example",
                    product_name="db",
                    minimum_version="1.0.0",
                ),
            ),
        )
        result = data.to_dict()
        assert result["extensions"]["require-stable-hostname"] is False
        assert len(result["extensions"]["product-dependencies"]) == 1
