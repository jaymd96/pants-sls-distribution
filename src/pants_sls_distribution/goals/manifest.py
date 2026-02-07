"""sls-manifest goal: generate deployment/manifest.yml for SLS targets."""

import os
from pathlib import Path

from pants.engine.console import Console
from pants.engine.goal import Goal, GoalSubsystem
from pants.engine.rules import Get, MultiGet, collect_rules, goal_rule
from pants.engine.target import FilteredTargets

from pants_sls_distribution.rules.manifest import (
    SlsManifest,
    SlsManifestFieldSet,
    SlsManifestRequest,
)
from pants_sls_distribution.targets import EntrypointField


class SlsManifestGoalSubsystem(GoalSubsystem):
    name = "sls-manifest"
    help = "Generate deployment/manifest.yml for SLS service targets."


class SlsManifestGoal(Goal):
    subsystem_cls = SlsManifestGoalSubsystem
    environment_behavior = Goal.EnvironmentBehavior.LOCAL_ONLY


@goal_rule
async def run_sls_manifest(
    console: Console,
    targets: FilteredTargets,
) -> SlsManifestGoal:
    sls_targets = [t for t in targets if t.has_field(EntrypointField)]

    if not sls_targets:
        console.print_stderr("No sls_service targets found.")
        return SlsManifestGoal(exit_code=0)

    manifests = await MultiGet(
        Get(
            SlsManifest,
            SlsManifestRequest(SlsManifestFieldSet.create(t)),
        )
        for t in sls_targets
    )

    dist_dir = Path("dist")
    dist_dir.mkdir(parents=True, exist_ok=True)

    for manifest in manifests:
        # Write to dist/<product-name>/deployment/manifest.yml
        output_dir = dist_dir / manifest.data.product_name / "deployment"
        output_dir.mkdir(parents=True, exist_ok=True)
        output_path = output_dir / "manifest.yml"
        output_path.write_text(manifest.content, encoding="utf-8")

        console.print_stdout(
            f"Generated manifest: {output_path} "
            f"({manifest.product_id} v{manifest.product_version})"
        )

    return SlsManifestGoal(exit_code=0)


def rules():
    return collect_rules()
