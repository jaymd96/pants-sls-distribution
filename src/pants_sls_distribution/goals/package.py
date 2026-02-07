"""sls-package goal: assemble SLS distribution and write to dist/."""

import os
import shutil
import tarfile
from pathlib import Path

from pants.engine.console import Console
from pants.engine.fs import Digest, DigestContents
from pants.engine.goal import Goal, GoalSubsystem
from pants.engine.rules import Get, MultiGet, collect_rules, goal_rule
from pants.engine.target import FilteredTargets

from pants_sls_distribution.rules.manifest import SlsManifestFieldSet
from pants_sls_distribution.targets import EntrypointField
from pants_sls_distribution.rules.package import (
    SlsPackageRequest,
    SlsPackageResult,
)


class SlsPackageGoalSubsystem(GoalSubsystem):
    name = "sls-package"
    help = "Package SLS service targets into distribution tarballs."


class SlsPackageGoal(Goal):
    subsystem_cls = SlsPackageGoalSubsystem
    environment_behavior = Goal.EnvironmentBehavior.LOCAL_ONLY


@goal_rule
async def run_sls_package(
    console: Console,
    targets: FilteredTargets,
) -> SlsPackageGoal:
    sls_targets = [t for t in targets if t.has_field(EntrypointField)]

    if not sls_targets:
        console.print_stderr("No sls_service targets found.")
        return SlsPackageGoal(exit_code=0)

    results = await MultiGet(
        Get(
            SlsPackageResult,
            SlsPackageRequest(SlsManifestFieldSet.create(t)),
        )
        for t in sls_targets
    )

    dist_dir = Path("dist")

    for result in results:
        layout = result.layout
        output_root = dist_dir / layout.dist_name

        # Clean previous output
        if output_root.exists():
            shutil.rmtree(output_root)

        # Create directories
        for d in layout.directories:
            (output_root / d.relative_path).mkdir(parents=True, exist_ok=True)

        # Write files
        for f in layout.files:
            file_path = output_root / f.relative_path
            file_path.parent.mkdir(parents=True, exist_ok=True)

            if f.content is not None:
                file_path.write_text(f.content, encoding="utf-8")
            elif f.source_path is not None:
                shutil.copy2(f.source_path, file_path)

            if f.executable:
                file_path.chmod(file_path.stat().st_mode | 0o111)

        # Write launcher binaries from Pants digest
        launcher_contents = await Get(DigestContents, Digest, result.launcher_digest)
        for file_content in launcher_contents:
            dest = output_root / file_content.path
            dest.parent.mkdir(parents=True, exist_ok=True)
            dest.write_bytes(file_content.content)
            dest.chmod(dest.stat().st_mode | 0o111)

        # Create tarball
        tarball_path = dist_dir / f"{layout.dist_name}.sls.tgz"
        with tarfile.open(tarball_path, "w:gz") as tar:
            tar.add(str(output_root), arcname=layout.dist_name)

        console.print_stdout(
            f"Packaged: {tarball_path} "
            f"({result.manifest.product_id} v{result.product_version})"
        )

    return SlsPackageGoal(exit_code=0)


def rules():
    return collect_rules()
