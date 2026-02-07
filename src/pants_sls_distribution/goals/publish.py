"""sls-publish goal: publish SLS distributions to Apollo Hub."""

from pants.engine.console import Console
from pants.engine.goal import Goal, GoalSubsystem
from pants.engine.rules import Get, MultiGet, collect_rules, goal_rule
from pants.engine.target import FilteredTargets
from pants.option.option_types import BoolOption

from pants_sls_distribution.rules.manifest import SlsManifestFieldSet
from pants_sls_distribution.targets import EntrypointField
from pants_sls_distribution.rules.publish import (
    SlsPublishRequest,
    SlsPublishResult,
)


class SlsPublishGoalSubsystem(GoalSubsystem):
    name = "sls-publish"
    help = "Publish SLS distributions to Apollo Hub."

    dry_run = BoolOption(
        default=False,
        help="Show what would be published without actually publishing.",
    )


class SlsPublishGoal(Goal):
    subsystem_cls = SlsPublishGoalSubsystem
    environment_behavior = Goal.EnvironmentBehavior.LOCAL_ONLY


@goal_rule
async def run_sls_publish(
    console: Console,
    targets: FilteredTargets,
    subsystem: SlsPublishGoalSubsystem,
) -> SlsPublishGoal:
    sls_targets = [t for t in targets if t.has_field(EntrypointField)]

    if not sls_targets:
        console.print_stderr("No sls_service targets found.")
        return SlsPublishGoal(exit_code=0)

    results = await MultiGet(
        Get(
            SlsPublishResult,
            SlsPublishRequest(
                field_set=SlsManifestFieldSet.create(t),
                dry_run=subsystem.dry_run,
            ),
        )
        for t in sls_targets
    )

    exit_code = 0
    for result in results:
        pub = result.result
        if pub.success:
            prefix = "[DRY RUN] " if pub.dry_run else ""
            console.print_stdout(
                f"{prefix}Published {result.product_id} v{result.product_version}: "
                f"{pub.message}"
            )
            if pub.release_id:
                console.print_stdout(f"  Release ID: {pub.release_id}")
        else:
            console.print_stderr(
                f"Failed to publish {result.product_id} v{result.product_version}: "
                f"{pub.message}"
            )
            exit_code = 1

    return SlsPublishGoal(exit_code=exit_code)


def rules():
    return collect_rules()
