"""Tests for launcher binary metadata (pure functions, no Pants engine)."""

from __future__ import annotations

from pants_sls_distribution._launcher_binary import (
    LAUNCHER_BINARY_NAME,
    LAUNCHER_PLATFORMS,
    launcher_asset_name,
    launcher_layout_path,
)


class TestLauncherPlatforms:
    """Test LAUNCHER_PLATFORMS constant."""

    def test_all_four_platforms_present(self):
        assert len(LAUNCHER_PLATFORMS) == 4

    def test_contains_darwin_amd64(self):
        assert ("darwin", "amd64") in LAUNCHER_PLATFORMS

    def test_contains_darwin_arm64(self):
        assert ("darwin", "arm64") in LAUNCHER_PLATFORMS

    def test_contains_linux_amd64(self):
        assert ("linux", "amd64") in LAUNCHER_PLATFORMS

    def test_contains_linux_arm64(self):
        assert ("linux", "arm64") in LAUNCHER_PLATFORMS

    def test_no_duplicates(self):
        assert len(LAUNCHER_PLATFORMS) == len(set(LAUNCHER_PLATFORMS))


class TestLauncherBinaryName:
    """Test LAUNCHER_BINARY_NAME constant."""

    def test_binary_name(self):
        assert LAUNCHER_BINARY_NAME == "python-service-launcher"


class TestLauncherLayoutPath:
    """Test launcher_layout_path() helper."""

    def test_linux_amd64(self):
        assert launcher_layout_path("linux", "amd64") == (
            "service/bin/linux-amd64/python-service-launcher"
        )

    def test_linux_arm64(self):
        assert launcher_layout_path("linux", "arm64") == (
            "service/bin/linux-arm64/python-service-launcher"
        )

    def test_darwin_amd64(self):
        assert launcher_layout_path("darwin", "amd64") == (
            "service/bin/darwin-amd64/python-service-launcher"
        )

    def test_darwin_arm64(self):
        assert launcher_layout_path("darwin", "arm64") == (
            "service/bin/darwin-arm64/python-service-launcher"
        )

    def test_all_platforms(self):
        for os_name, arch in LAUNCHER_PLATFORMS:
            path = launcher_layout_path(os_name, arch)
            assert path.startswith("service/bin/")
            assert path.endswith("/python-service-launcher")
            assert f"{os_name}-{arch}" in path


class TestLauncherAssetName:
    """Test launcher_asset_name() helper."""

    def test_linux_amd64(self):
        assert launcher_asset_name("linux", "amd64") == (
            "python-service-launcher-linux-amd64"
        )

    def test_linux_arm64(self):
        assert launcher_asset_name("linux", "arm64") == (
            "python-service-launcher-linux-arm64"
        )

    def test_darwin_amd64(self):
        assert launcher_asset_name("darwin", "amd64") == (
            "python-service-launcher-darwin-amd64"
        )

    def test_darwin_arm64(self):
        assert launcher_asset_name("darwin", "arm64") == (
            "python-service-launcher-darwin-arm64"
        )

    def test_all_platforms(self):
        for os_name, arch in LAUNCHER_PLATFORMS:
            name = launcher_asset_name(os_name, arch)
            assert name.startswith("python-service-launcher-")
            assert f"{os_name}-{arch}" in name
