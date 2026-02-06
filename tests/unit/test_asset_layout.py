"""Tests for asset layout assembly (pure functions, no Pants engine)."""

from __future__ import annotations

from pants_sls_distribution._asset_layout import (
    AssetMapping,
    build_asset_layout,
)
from pants_sls_distribution._layout import layout_to_file_map


class TestAssetMapping:
    """Test AssetMapping dataclass."""

    def test_basic_mapping(self):
        m = AssetMapping(source_path="/src/file.txt", dest_path="data/file.txt")
        assert m.source_path == "/src/file.txt"
        assert m.dest_path == "data/file.txt"


class TestBuildAssetLayout:
    """Test asset distribution layout assembly."""

    def test_basic_layout(self):
        layout = build_asset_layout(
            product_name="my-assets",
            product_version="1.0.0",
            manifest_yaml="manifest-version: '1.0'\n",
        )
        assert layout.dist_name == "my-assets-1.0.0"

    def test_contains_manifest(self):
        layout = build_asset_layout(
            product_name="my-assets",
            product_version="1.0.0",
            manifest_yaml="manifest content",
        )
        files = {f.relative_path: f for f in layout.files}
        assert "deployment/manifest.yml" in files
        assert files["deployment/manifest.yml"].content == "manifest content"

    def test_contains_asset_directory(self):
        layout = build_asset_layout(
            product_name="my-assets",
            product_version="1.0.0",
            manifest_yaml="m",
        )
        dir_paths = {d.relative_path for d in layout.directories}
        assert "asset" in dir_paths

    def test_no_service_directories(self):
        """Asset layouts should NOT have service/, var/, etc."""
        layout = build_asset_layout(
            product_name="my-assets",
            product_version="1.0.0",
            manifest_yaml="m",
        )
        file_paths = {f.relative_path for f in layout.files}
        dir_paths = {d.relative_path for d in layout.directories}

        assert not any("service/" in p for p in file_paths)
        assert not any("var/" in p for p in dir_paths)
        assert "service/bin/init.sh" not in file_paths

    def test_with_lock_file(self):
        layout = build_asset_layout(
            product_name="my-assets",
            product_version="1.0.0",
            manifest_yaml="m",
            lock_file_content="# lock\ncom.example:dep (1.0.0, 1.x.x)\n",
        )
        files = {f.relative_path: f for f in layout.files}
        assert "deployment/product-dependencies.lock" in files

    def test_without_lock_file(self):
        layout = build_asset_layout(
            product_name="my-assets",
            product_version="1.0.0",
            manifest_yaml="m",
        )
        file_paths = {f.relative_path for f in layout.files}
        assert "deployment/product-dependencies.lock" not in file_paths

    def test_with_asset_mappings(self):
        mappings = [
            AssetMapping(source_path="/src/index.html", dest_path="web/index.html"),
            AssetMapping(source_path="/src/style.css", dest_path="web/style.css"),
            AssetMapping(source_path="/src/config.json", dest_path="conf/config.json"),
        ]
        layout = build_asset_layout(
            product_name="frontend",
            product_version="2.0.0",
            manifest_yaml="m",
            asset_mappings=mappings,
        )
        files = {f.relative_path: f for f in layout.files}
        assert "asset/web/index.html" in files
        assert "asset/web/style.css" in files
        assert "asset/conf/config.json" in files
        # Source paths preserved
        assert files["asset/web/index.html"].source_path == "/src/index.html"

    def test_no_asset_mappings(self):
        layout = build_asset_layout(
            product_name="my-assets",
            product_version="1.0.0",
            manifest_yaml="m",
        )
        # Only manifest file, no asset files
        file_paths = {f.relative_path for f in layout.files}
        assert file_paths == {"deployment/manifest.yml"}

    def test_dist_name_format(self):
        layout = build_asset_layout(
            product_name="frontend-assets",
            product_version="3.1.0-rc2",
            manifest_yaml="m",
        )
        assert layout.dist_name == "frontend-assets-3.1.0-rc2"


class TestAssetLayoutFileMap:
    """Test layout_to_file_map with asset layouts."""

    def test_file_map_content_only(self):
        layout = build_asset_layout(
            product_name="my-assets",
            product_version="1.0.0",
            manifest_yaml="manifest content",
            lock_file_content="lock content",
        )
        file_map = layout_to_file_map(layout)
        assert file_map == {
            "deployment/manifest.yml": "manifest content",
            "deployment/product-dependencies.lock": "lock content",
        }

    def test_file_map_excludes_source_paths(self):
        layout = build_asset_layout(
            product_name="my-assets",
            product_version="1.0.0",
            manifest_yaml="m",
            asset_mappings=[
                AssetMapping(source_path="/src/file.txt", dest_path="data/file.txt"),
            ],
        )
        file_map = layout_to_file_map(layout)
        # Source-path files are NOT in the content map
        assert "asset/data/file.txt" not in file_map
        assert "deployment/manifest.yml" in file_map


class TestAssetLayoutIntegration:
    """Integration tests for full asset layout scenarios."""

    def test_complete_asset_distribution(self):
        mappings = [
            AssetMapping("/build/bundle.js", "web/bundle.js"),
            AssetMapping("/build/index.html", "web/index.html"),
            AssetMapping("/configs/app.yml", "conf/app.yml"),
        ]
        layout = build_asset_layout(
            product_name="my-frontend",
            product_version="1.5.0",
            manifest_yaml="manifest-version: '1.0'\nproduct-type: asset.v1\n",
            lock_file_content="# lock\ncom.example:api (2.0.0, 2.x.x)\n",
            asset_mappings=mappings,
        )

        assert layout.dist_name == "my-frontend-1.5.0"

        file_paths = {f.relative_path for f in layout.files}
        assert "deployment/manifest.yml" in file_paths
        assert "deployment/product-dependencies.lock" in file_paths
        assert "asset/web/bundle.js" in file_paths
        assert "asset/web/index.html" in file_paths
        assert "asset/conf/app.yml" in file_paths

        dir_paths = {d.relative_path for d in layout.directories}
        assert "asset" in dir_paths

        # Total: 1 manifest + 1 lock + 3 assets = 5 files
        assert len(layout.files) == 5
