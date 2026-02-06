"""Global SLS distribution configuration subsystem."""

from __future__ import annotations

from pants.option.option_types import BoolOption, StrOption
from pants.option.subsystem import Subsystem


class SlsDistributionSubsystem(Subsystem):
    """Global configuration for SLS distribution packaging."""

    options_scope = "sls-distribution"
    help = "Configuration for the SLS distribution packaging plugin."

    default_python_version = StrOption(
        default="3.11",
        help="Default Python version for SLS services.",
    )

    default_command = StrOption(
        default="uvicorn",
        help="Default command for starting Python services.",
    )

    docker_base_image = StrOption(
        default="python:3.11-slim",
        help="Base Docker image for SLS distributions.",
    )

    docker_registry = StrOption(
        default="",
        help="Docker registry URL (e.g., registry.example.io).",
    )

    apollo_hub_url = StrOption(
        default="",
        help="Apollo Hub URL for publishing (e.g., http://localhost:8000).",
    )

    apollo_auth_token = StrOption(
        default="",
        help="Bearer token for Apollo Hub authentication. Can also be set via APOLLO_AUTH_TOKEN env var.",
    )

    publish_channel = StrOption(
        default="",
        help="Override the default publish channel (stable, beta, dev). Empty = auto-detect from version.",
    )

    install_path = StrOption(
        default="/opt/services",
        help="Install path for SLS distribution inside Docker container.",
    )

    manifest_version = StrOption(
        default="1.0",
        help="Manifest version string. Should not normally be changed.",
    )

    strict_validation = BoolOption(
        default=True,
        help="Enable strict manifest validation against JSON schema.",
    )
