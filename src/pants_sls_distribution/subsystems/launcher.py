"""Subsystem for python-service-launcher binary downloads.

Uses a plain Subsystem (NOT ExternalTool) because ExternalTool only downloads
for the current host platform, whereas SLS distributions need all 4 platform
binaries bundled together.
"""

from __future__ import annotations

from pants.engine.fs import FileDigest
from pants.option.option_types import StrListOption, StrOption
from pants.option.subsystem import Subsystem

from pants_sls_distribution._launcher_binary import (
    LAUNCHER_PLATFORMS,
    launcher_asset_name,
)


class PythonServiceLauncherSubsystem(Subsystem):
    """python-service-launcher Go binary for SLS distributions."""

    options_scope = "python-service-launcher"
    help = "Configuration for downloading python-service-launcher platform binaries."

    version = StrOption(
        default="v0.1.0",
        help="Version tag to download from GitHub releases.",
    )

    github_repo = StrOption(
        default="jaymd96/python-service-launcher",
        help="GitHub repository (owner/repo) hosting release assets.",
    )

    known_versions = StrListOption(
        default=[
            "v0.1.0|darwin|amd64|d21d60df15d83436ccfd2c1396d241ed2148ce9b0076f20b2a240ef5ecce1f4f|2659536",
            "v0.1.0|darwin|arm64|ecba5286cc53acda759d6d48614b1cec53d1145a43ceb7d34669d40d78cc8cd8|2585746",
            "v0.1.0|linux|amd64|817b5ee9bbba2d3a9bf2edbce6432c8b49260c5e2e61fe9ef4d14abd3bb3da4d|2678968",
            "v0.1.0|linux|arm64|945119ab3b09235eee9d4fb44ac252cdf2e635282e0a50a91a85a7add8549ac7|2621624",
        ],
        help=(
            "Known version entries: 'version|os|arch|sha256|size'. "
            "Each entry pins a specific binary by content hash and file size."
        ),
    )

    def download_url(self, os_name: str, arch: str) -> str:
        """Build the GitHub release download URL for a platform binary."""
        asset = launcher_asset_name(os_name, arch)
        return (
            f"https://github.com/{self.github_repo}/"
            f"releases/download/{self.version}/{asset}"
        )

    def file_digest(self, os_name: str, arch: str) -> FileDigest | None:
        """Look up the FileDigest for a specific platform from known_versions.

        Returns None if no matching entry is found (e.g. placeholder hashes).
        """
        for entry in self.known_versions:
            parts = entry.split("|")
            if len(parts) != 5:
                continue
            ver, entry_os, entry_arch, sha256, size_str = parts
            if ver == self.version and entry_os == os_name and entry_arch == arch:
                if sha256.startswith("<"):
                    return None
                return FileDigest(fingerprint=sha256, serialized_bytes_length=int(size_str))
        return None
