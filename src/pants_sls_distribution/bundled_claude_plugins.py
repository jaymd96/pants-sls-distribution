"""Bundled Claude Code plugins for pants-sls-distribution.

When pants-claude-plugins is installed alongside this backend, these plugins
are automatically discovered and installed when users run:

    pants claude-install --include-bundled ::

This bundles skills for the full SLS deployment pipeline:
  - deploy-to-apollo: End-to-end deployment workflow guide
  - sls-distribution: Pants goals, targets, and configuration
  - docker-generator: Dockerfile generation (directives, builder, presets)
  - release-hub: Release publishing with version detection and retry
  - service-launcher: Container-aware Go launcher with memory management
"""

# Marketplaces to add before installing plugins.
# Each entry is a GitHub "owner/repo" whose .claude-plugin/ directory
# is the marketplace source.
BUNDLED_MARKETPLACES = [
    "jaymd96/pants-sls-distribution",
    "jaymd96/pants-docker-generator",
    "jaymd96/pants-release-hub",
    "jaymd96/python-service-launcher",
    "jaymd96/deploy-to-apollo",
]

# Claude Code plugins to install.
# "marketplace" must match the "name" field in each repo's plugin.json.
BUNDLED_CLAUDE_PLUGINS = [
    # Orchestrator plugin (this package)
    {
        "plugin": "sls-distribution",
        "marketplace": "sls-distribution",
        "scope": "project",
        "description": "SLS distribution packaging: manifest, validate, package, docker, publish, lock goals",
    },
    # Downstream tool: Dockerfile generation
    {
        "plugin": "docker-generator",
        "marketplace": "docker-generator",
        "scope": "project",
        "description": "Dockerfile generation with directives, builder pattern, and SLS presets",
    },
    # Downstream tool: release publishing
    {
        "plugin": "release-hub",
        "marketplace": "release-hub",
        "scope": "project",
        "description": "Release publishing with multi-format version detection and retry",
    },
    # Downstream tool: Python service launcher
    {
        "plugin": "service-launcher",
        "marketplace": "service-launcher",
        "scope": "project",
        "description": "Container-aware Python launcher with memory management and RSS watchdog",
    },
    # Deployment workflow guide
    {
        "plugin": "deploy-to-apollo",
        "marketplace": "deploy-to-apollo",
        "scope": "project",
        "description": "End-to-end deployment workflow for Python services to Apollo",
    },
]
