"""sls-validate goal: validate manifests and dependency constraints."""

from __future__ import annotations

from pants.engine.console import Console
from pants.engine.goal import Goal, GoalSubsystem
from pants.engine.rules import Get, MultiGet, collect_rules, goal_rule
from pants.engine.target import FilteredTargets

from pants_sls_distribution.rules.manifest import (
    SlsManifest,
    SlsManifestFieldSet,
    SlsManifestRequest,
)
from pants_sls_distribution.rules.validation import (
    SlsValidationRequest,
    SlsValidationResult,
)


class SlsValidateGoalSubsystem(GoalSubsystem):
    name = "sls-validate"
    help = "Validate SLS manifests against schema and semantic rules."


class SlsValidateGoal(Goal):
    subsystem_cls = SlsValidateGoalSubsystem
    environment_behavior = Goal.EnvironmentBehavior.LOCAL_ONLY


@goal_rule
async def run_sls_validate(
    console: Console,
    targets: FilteredTargets,
) -> SlsValidateGoal:
    sls_targets = [
        t for t in targets
        if t.has_field(SlsManifestFieldSet.required_fields[0])
    ]

    if not sls_targets:
        console.print_stderr("No sls_service targets found.")
        return SlsValidateGoal(exit_code=0)

    # Generate manifests first
    manifests = await MultiGet(
        Get(
            SlsManifest,
            SlsManifestRequest(SlsManifestFieldSet.create(t)),
        )
        for t in sls_targets
    )

    # Validate each manifest
    results = await MultiGet(
        Get(
            SlsValidationResult,
            SlsValidationRequest(manifest),
        )
        for manifest in manifests
    )

    has_errors = False
    for manifest, result in zip(manifests, results):
        if result.valid:
            console.print_stdout(f"PASS  {manifest.product_id} v{manifest.product_version}")
        else:
            has_errors = True
            console.print_stderr(f"FAIL  {manifest.product_id} v{manifest.product_version}")
            for error in result.errors:
                console.print_stderr(f"  ERROR: {error}")

        for warning in result.warnings:
            console.print_stderr(f"  WARN: {warning}")

    if has_errors:
        console.print_stderr("\nValidation failed.")
        return SlsValidateGoal(exit_code=1)

    console.print_stdout(f"\nAll {len(manifests)} manifest(s) valid.")
    return SlsValidateGoal(exit_code=0)


def rules():
    return collect_rules()
