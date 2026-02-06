"""sls-lock goal: generate product-dependencies.lock files."""

from __future__ import annotations

from pathlib import Path

from pants.engine.console import Console
from pants.engine.goal import Goal, GoalSubsystem
from pants.engine.rules import Get, MultiGet, collect_rules, goal_rule
from pants.engine.target import FilteredTargets

from pants_sls_distribution.rules.dependencies import (
    SlsLockFileRequest,
    SlsLockFileResult,
)
from pants_sls_distribution.rules.manifest import SlsManifestFieldSet


class SlsLockGoalSubsystem(GoalSubsystem):
    name = "sls-lock"
    help = "Generate product-dependencies.lock files for SLS service targets."


class SlsLockGoal(Goal):
    subsystem_cls = SlsLockGoalSubsystem
    environment_behavior = Goal.EnvironmentBehavior.LOCAL_ONLY


@goal_rule
async def run_sls_lock(
    console: Console,
    targets: FilteredTargets,
) -> SlsLockGoal:
    sls_targets = [t for t in targets if t.has_field(SlsManifestFieldSet.required_fields[0])]

    if not sls_targets:
        console.print_stderr("No sls_service targets found.")
        return SlsLockGoal(exit_code=0)

    results = await MultiGet(
        Get(
            SlsLockFileResult,
            SlsLockFileRequest(SlsManifestFieldSet.create(t)),
        )
        for t in sls_targets
    )

    dist_dir = Path("dist")

    for result in results:
        if result.dependency_count == 0:
            console.print_stdout(
                f"No dependencies for {result.product_id} (skipping lock file)"
            )
            continue

        # Write lock file alongside the manifest
        product_name = result.product_id.split(":")[-1]
        output_dir = dist_dir / product_name / "deployment"
        output_dir.mkdir(parents=True, exist_ok=True)
        lock_path = output_dir / "product-dependencies.lock"
        lock_path.write_text(result.content, encoding="utf-8")

        console.print_stdout(
            f"Generated lock file: {lock_path} "
            f"({result.product_id}, {result.dependency_count} dependencies)"
        )

    return SlsLockGoal(exit_code=0)


def rules():
    return collect_rules()
