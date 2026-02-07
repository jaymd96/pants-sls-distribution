"""SLS launcher binary download rule.

Downloads python-service-launcher binaries for all supported platforms
and merges them into a single Digest for inclusion in the SLS distribution.
"""

import logging
from dataclasses import dataclass
from typing import Optional

from pants.engine.fs import (
    AddPrefix,
    CreateDigest,
    Digest,
    DigestContents,
    DownloadFile,
    FileContent,
    FileDigest,
    MergeDigests,
)
from pants.engine.process import Process, ProcessResult
from pants.engine.rules import Get, MultiGet, collect_rules, rule

from pants_sls_distribution._launcher_binary import (
    LAUNCHER_BINARY_NAME,
    LAUNCHER_PLATFORMS,
    launcher_asset_name,
)
from pants_sls_distribution.subsystems.launcher import (
    PythonServiceLauncherSubsystem,
)

logger = logging.getLogger(__name__)


# =============================================================================
# Request / Result types
# =============================================================================


@dataclass(frozen=True)
class LauncherBinariesRequest:
    """Request to download all platform launcher binaries."""


@dataclass(frozen=True)
class LauncherBinariesResult:
    """Result containing a Digest with all 4 platform binaries.

    The digest contains files at:
        service/bin/<os>-<arch>/python-service-launcher
    for each platform in LAUNCHER_PLATFORMS.
    """

    digest: Digest


# =============================================================================
# Internal types
# =============================================================================


@dataclass(frozen=True)
class _SingleLauncherDownload:
    """Internal: request to download and place a single platform binary."""

    os_name: str
    arch: str
    url: str
    expected_digest: Optional[FileDigest]


@dataclass(frozen=True)
class _SingleLauncherResult:
    """Internal: result of downloading a single platform binary."""

    digest: Digest


# =============================================================================
# Rules
# =============================================================================


@rule(desc="Download a single python-service-launcher binary")
async def _download_single_launcher(
    request: _SingleLauncherDownload,
) -> _SingleLauncherResult:
    if request.expected_digest is not None:
        # Use DownloadFile with verified digest (preferred path)
        downloaded = await Get(
            Digest,
            DownloadFile(url=request.url, expected_digest=request.expected_digest),
        )
    else:
        # Fall back to curl when digest is unknown (placeholder hashes)
        result = await Get(
            ProcessResult,
            Process(
                argv=[
                    "curl",
                    "-fSL",
                    "--retry", "3",
                    "-o", LAUNCHER_BINARY_NAME,
                    request.url,
                ],
                description=f"Download {launcher_asset_name(request.os_name, request.arch)}",
                output_files=(LAUNCHER_BINARY_NAME,),
            ),
        )
        downloaded = result.output_digest

    # Place the binary at the correct layout path
    prefixed = await Get(
        Digest,
        AddPrefix(downloaded, f"service/bin/{request.os_name}-{request.arch}"),
    )
    return _SingleLauncherResult(digest=prefixed)


@rule(desc="Download python-service-launcher binaries for all platforms")
async def download_launcher_binaries(
    request: LauncherBinariesRequest,
    launcher_subsystem: PythonServiceLauncherSubsystem,
) -> LauncherBinariesResult:
    # Download all platform binaries in parallel
    single_results = await MultiGet(
        Get(
            _SingleLauncherResult,
            _SingleLauncherDownload(
                os_name=os_name,
                arch=arch,
                url=launcher_subsystem.download_url(os_name, arch),
                expected_digest=launcher_subsystem.file_digest(os_name, arch),
            ),
        )
        for os_name, arch in LAUNCHER_PLATFORMS
    )

    # Merge all platform binaries into a single digest
    merged = await Get(
        Digest,
        MergeDigests(r.digest for r in single_results),
    )

    # Re-create with executable permissions
    contents = await Get(DigestContents, Digest, merged)
    executable_files = []
    for fc in contents:
        executable_files.append(
            FileContent(
                path=fc.path,
                content=fc.content,
                is_executable=True,
            )
        )

    if executable_files:
        merged = await Get(Digest, CreateDigest(executable_files))

    logger.info(
        "Downloaded python-service-launcher %s for %d platforms",
        launcher_subsystem.version,
        len(LAUNCHER_PLATFORMS),
    )

    return LauncherBinariesResult(digest=merged)


def rules():
    return collect_rules()
