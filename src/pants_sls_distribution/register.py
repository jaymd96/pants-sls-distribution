"""Pants plugin registration for SLS distribution packaging.

Backend path: pants_sls_distribution

Enable in pants.toml:

    [GLOBAL]
    backend_packages = [
        "pants_sls_distribution",
    ]

    [sls-distribution]
    docker_base_image = "python:3.11-slim"
    docker_registry = "registry.example.io"
"""

from __future__ import annotations

from typing import Iterable, Type

from pants.engine.rules import Rule, collect_rules
from pants.option.subsystem import Subsystem

from pants_sls_distribution.goals import docker as docker_goal
from pants_sls_distribution.goals import lock as lock_goal
from pants_sls_distribution.goals import manifest as manifest_goal
from pants_sls_distribution.goals import package as package_goal
from pants_sls_distribution.goals import publish as publish_goal
from pants_sls_distribution.goals import validate as validate_goal
from pants_sls_distribution.rules import dependencies as dependencies_rule
from pants_sls_distribution.rules import docker as docker_rule
from pants_sls_distribution.rules import launcher as launcher_rule
from pants_sls_distribution.rules import manifest as manifest_rule
from pants_sls_distribution.rules import package as package_rule
from pants_sls_distribution.rules import publish as publish_rule
from pants_sls_distribution.rules import validation as validation_rule
from pants_sls_distribution.subsystem import SlsDistributionSubsystem
from pants_sls_distribution.subsystems.launcher import (
    PythonServiceLauncherSubsystem,
)
from pants_sls_distribution.targets import (
    SlsArtifactTarget,
    SlsAssetTarget,
    SlsProductDependencyTarget,
    SlsProductIncompatibilityTarget,
    SlsServiceTarget,
)


def rules() -> Iterable[Rule]:
    return [
        *manifest_rule.rules(),
        *validation_rule.rules(),
        *package_rule.rules(),
        *launcher_rule.rules(),
        *docker_rule.rules(),
        *dependencies_rule.rules(),
        *publish_rule.rules(),
        *manifest_goal.rules(),
        *validate_goal.rules(),
        *package_goal.rules(),
        *docker_goal.rules(),
        *lock_goal.rules(),
        *publish_goal.rules(),
    ]


def target_types() -> Iterable[type]:
    return [
        SlsServiceTarget,
        SlsAssetTarget,
        SlsProductDependencyTarget,
        SlsProductIncompatibilityTarget,
        SlsArtifactTarget,
    ]


def subsystems() -> Iterable[Type[Subsystem]]:
    return [SlsDistributionSubsystem, PythonServiceLauncherSubsystem]
