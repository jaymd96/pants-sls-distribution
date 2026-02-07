"""sls-docker goal: generate Dockerfiles and optionally build images."""

from __future__ import annotations

from pathlib import Path

from pants.engine.console import Console
from pants.engine.goal import Goal, GoalSubsystem
from pants.engine.rules import Get, MultiGet, collect_rules, goal_rule
from pants.engine.target import FilteredTargets

from pants_sls_distribution.rules.docker import (
    SlsDockerRequest,
    SlsDockerResult,
)
from pants_sls_distribution.rules.manifest import SlsManifestFieldSet


class SlsDockerGoalSubsystem(GoalSubsystem):
    name = "sls-docker"
    help = "Generate Dockerfiles for SLS service targets."


class SlsDockerGoal(Goal):
    subsystem_cls = SlsDockerGoalSubsystem
    environment_behavior = Goal.EnvironmentBehavior.LOCAL_ONLY


@goal_rule
async def run_sls_docker(
    console: Console,
    targets: FilteredTargets,
) -> SlsDockerGoal:
    sls_targets = [t for t in targets if t.has_field(SlsManifestFieldSet.required_fields[0])]

    if not sls_targets:
        console.print_stderr("No sls_service targets found.")
        return SlsDockerGoal(exit_code=0)

    results = await MultiGet(
        Get(
            SlsDockerResult,
            SlsDockerRequest(SlsManifestFieldSet.create(t)),
        )
        for t in sls_targets
    )

    dist_dir = Path("dist")

    for result in results:
        pkg = result.package_result
        docker_dir = dist_dir / pkg.dist_name / "docker"
        docker_dir.mkdir(parents=True, exist_ok=True)

        # Write Dockerfile
        dockerfile_path = docker_dir / "Dockerfile"
        dockerfile_path.write_text(result.dockerfile_content, encoding="utf-8")

        # Write .dockerignore
        dockerignore_path = docker_dir / ".dockerignore"
        dockerignore_path.write_text(result.dockerignore_content, encoding="utf-8")

        # Write hook init system files for Docker build context
        if result.hook_entrypoint_content is not None:
            hooks_dir = docker_dir / "hooks"
            hooks_dir.mkdir(parents=True, exist_ok=True)

            entrypoint_path = hooks_dir / "entrypoint.sh"
            entrypoint_path.write_text(result.hook_entrypoint_content, encoding="utf-8")

            library_path = hooks_dir / "hooks.sh"
            library_path.write_text(result.hook_library_content, encoding="utf-8")

            console.print_stdout(
                f"  Hook init system: {hooks_dir}"
            )

        image_tag = f"{pkg.product_name}:{pkg.product_version}"
        console.print_stdout(
            f"Generated Dockerfile: {dockerfile_path} "
            f"(image: {image_tag})"
        )

    return SlsDockerGoal(exit_code=0)


def rules():
    return collect_rules()
