"""Pure Python launcher binary metadata (no Pants dependencies).

Constants and helpers for the python-service-launcher Go binary that
is bundled into SLS distributions for all supported platforms.
"""

LAUNCHER_BINARY_NAME = "python-service-launcher"

LAUNCHER_PLATFORMS: tuple[tuple[str, str], ...] = (
    ("darwin", "amd64"),
    ("darwin", "arm64"),
    ("linux", "amd64"),
    ("linux", "arm64"),
)


def launcher_layout_path(os_name: str, arch: str) -> str:
    """Return the relative path within the SLS layout for a launcher binary.

    Example: launcher_layout_path("linux", "amd64")
             -> "service/bin/linux-amd64/python-service-launcher"
    """
    return f"service/bin/{os_name}-{arch}/{LAUNCHER_BINARY_NAME}"


def launcher_asset_name(os_name: str, arch: str) -> str:
    """Return the GitHub release asset name for a platform binary.

    Example: launcher_asset_name("linux", "amd64")
             -> "python-service-launcher-linux-amd64"
    """
    return f"{LAUNCHER_BINARY_NAME}-{os_name}-{arch}"
