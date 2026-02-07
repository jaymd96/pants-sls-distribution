"""Pure Python asset layout assembly (no Pants dependencies).

Assembles the directory tree for an SLS asset distribution (product-type: asset.v1):

    <product-name>-<version>/
        deployment/
            manifest.yml
            product-dependencies.lock   (if dependencies exist)
        asset/
            <files organized by destination path>
"""

from dataclasses import dataclass, field
from typing import List, Optional

from pants_sls_distribution._layout import LayoutFile, LayoutDirectory, SlsLayout


@dataclass(frozen=True)
class AssetMapping:
    """A mapping from source file to destination path in the asset directory."""

    source_path: str  # Path to source file on disk
    dest_path: str  # Relative path under asset/ in the distribution


def build_asset_layout(
    *,
    product_name: str,
    product_version: str,
    manifest_yaml: str,
    lock_file_content: Optional[str] = None,
    asset_mappings: Optional[List[AssetMapping]] = None,
) -> SlsLayout:
    """Build the complete SLS asset distribution layout.

    Args:
        product_name: SLS product name.
        product_version: SLS product version.
        manifest_yaml: Content of deployment/manifest.yml.
        lock_file_content: Content of product-dependencies.lock (if deps exist).
        asset_mappings: List of source->destination file mappings for asset/.

    Returns:
        SlsLayout with all files and directories.
    """
    dist_name = f"{product_name}-{product_version}"
    layout = SlsLayout(dist_name=dist_name)

    # --- deployment/ ---
    layout.add_file("deployment/manifest.yml", content=manifest_yaml)

    if lock_file_content is not None:
        layout.add_file("deployment/product-dependencies.lock", content=lock_file_content)

    # --- asset/ ---
    layout.add_directory("asset")

    if asset_mappings:
        for mapping in asset_mappings:
            dest = f"asset/{mapping.dest_path}"
            layout.add_file(dest, source_path=mapping.source_path)

    return layout
