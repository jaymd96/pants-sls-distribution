---
description: Pants plugin for SLS distribution packaging - manifest, validate, package, docker, publish, lock goals
user_invocable: true
triggers:
  - "sls"
  - "sls distribution"
  - "sls service"
  - "sls manifest"
  - "sls docker"
  - "sls publish"
  - "sls package"
  - "sls validate"
  - "pants sls"
---

# SLS Distribution

You are an expert on the `pants-sls-distribution` Pants plugin (v0.1.0). This plugin orchestrates three standalone tools to package Python services as SLS distributions. Use this knowledge to help developers configure and use the plugin.

## Overview

A Pants build system plugin that:
- Generates SLS manifests (`deployment/manifest.yml`)
- Validates manifest structure and constraints
- Packages Python services into distribution tarballs (`.sls.tgz`)
- Generates Dockerfiles and builds images
- Publishes releases to Apollo Hub
- Manages product dependency lock files

## How the 3 Tools Fit Together

```
                    pants-sls-distribution (Pants plugin)
                   /            |               \
    pants-docker-generator  pants-release-hub  python-service-launcher
    (Dockerfile generation) (release publishing) (Go binary, bundled)
```

| Tool | How SLS Distribution Uses It |
|------|------------------------------|
| **docker-generator** | `sls_dockerfile()` preset generates Dockerfiles; `sls_dockerignore()` generates .dockerignore |
| **release-hub** | `ApolloHubClient` publishes releases; `detect_version()` determines release type and channel |
| **service-launcher** | Go binaries for all 4 platforms are downloaded and bundled into the distribution tarball at `service/bin/<arch>/` |

For detailed integration patterns see [reference/integration-map.md](reference/integration-map.md).

## Quick Start

### pants.toml

```toml
[GLOBAL]
backend_packages = [
    "pants_sls_distribution",
]

[sls-distribution]
docker_base_image = "python:3.11-slim"
docker_registry = "registry.example.io"
apollo_hub_url = "https://hub.example.com"
apollo_auth_token = "my-token"
install_path = "/opt/services"

[python-service-launcher]
version = "v0.1.0"
github_repo = "jaymd96/python-service-launcher"
```

### Minimal BUILD file

```python
sls_service(
    name="my-service",
    product_group="com.example",
    product_name="my-service",
    version="1.0.0",
    entrypoint="app:app",
)
```

### Run goals

```bash
pants sls-manifest ::      # Generate manifest
pants sls-validate ::      # Validate manifest
pants sls-package ::       # Package distribution tarball
pants sls-docker ::        # Generate Dockerfile
pants sls-publish ::       # Publish to Apollo Hub
pants sls-lock ::          # Generate dependency lock file
```

## Target Types

### sls_service

The primary target type. Represents a Python service packaged as an SLS distribution.

```python
sls_service(
    name="my-service",
    # Identity (required)
    product_group="com.example",
    product_name="my-service",
    version="1.0.0",
    entrypoint="app:app",               # module:callable
    # Optional service config
    command="uvicorn",                   # default
    args=["--host", "0.0.0.0", "--port", "8080"],  # default
    python_version="3.11",              # default
    product_type="helm.v1",             # default
    env={"MY_VAR": "value"},
    pex_binary="service/lib/myservice.pex",
    # Health checks (mutually exclusive)
    check_args=["--check"],             # Same PEX, different args
    # check_command="python -m app.healthcheck",
    # check_script="scripts/check.sh",
    # Hooks
    hooks={
        "pre-startup.d/10-migrate.sh": "scripts/migrate.sh",
        "configure.d/20-config.sh": "scripts/configure.sh",
    },
    # Resources
    resource_requests={"cpu": "100m", "memory": "128Mi"},
    resource_limits={"cpu": "500m", "memory": "512Mi"},
    replication_desired=3,
    replication_min=2,
    replication_max=10,
    # Dependencies
    product_dependencies=[":database-dep"],
    product_incompatibilities=[":legacy-incompat"],
    artifacts=[":docker-image"],
    # Metadata
    labels={"team": "platform"},
    annotations={"description": "My service"},
    traits=["api", "web"],
    manifest_extensions={"custom-key": "value"},
)
```

### sls_asset

Static file distribution (no runtime, no init script, no health checks).

```python
sls_asset(
    name="frontend-assets",
    product_group="com.example",
    product_name="frontend-assets",
    version="1.0.0",
    product_type="asset.v1",
    assets={
        "static/": "web/static/",
        "config/": "conf/",
    },
)
```

### sls_product_dependency

```python
sls_product_dependency(
    name="database-dep",
    product_group="com.example",
    product_name="sample-database",
    minimum_version="1.0.0",
    maximum_version="2.0.0",     # Optional, defaults to major.x.x
    recommended_version="1.5.0", # Optional
    optional=False,              # Default
)
```

### sls_product_incompatibility

```python
sls_product_incompatibility(
    name="legacy-incompat",
    product_group="com.example",
    product_name="legacy-service",
    version_range="< 2.0.0",
    reason="Incompatible API",
)
```

### sls_artifact

```python
sls_artifact(
    name="docker-image",
    type="oci",                          # Default
    uri="registry.example.io/my-service:1.0.0",
    artifact_name="my-service",          # Optional
    digest="sha256:abc123...",           # Optional
)
```

For full field reference see [reference/targets-reference.md](reference/targets-reference.md).

## Goals

### sls-manifest

Generates `deployment/manifest.yml` for each `sls_service` target.

```bash
pants sls-manifest path/to/service:my-service
# Output: dist/my-service/deployment/manifest.yml
```

### sls-validate

Validates generated manifests against schema and semantic rules.

```bash
pants sls-validate ::
# PASS  com.example:my-service v1.0.0
# All 1 manifest(s) valid.
```

### sls-package

Assembles the full SLS distribution directory layout and creates a `.sls.tgz` tarball.

```bash
pants sls-package ::
# Packaged: dist/my-service-1.0.0.sls.tgz (com.example:my-service v1.0.0)
```

The tarball contains:
- `deployment/manifest.yml`
- `service/bin/init.sh`
- `service/bin/launcher-static.yml`
- `service/bin/<arch>/python-service-launcher` (4 platforms)
- `service/monitoring/bin/check.sh` (if health check configured)
- `var/data/tmp/`, `var/log/`, `var/run/`, `var/conf/`, `var/state/`
- Hook scripts (if configured)

### sls-docker

Generates a Dockerfile and .dockerignore for Docker image builds.

```bash
pants sls-docker ::
# Generated Dockerfile: dist/my-service-1.0.0/docker/Dockerfile (image: my-service:1.0.0)
```

Uses `pants-docker-generator`'s `sls_dockerfile()` preset internally.

### sls-publish

Publishes to Apollo Hub using `pants-release-hub`'s `ApolloHubClient`.

```bash
pants sls-publish ::
pants sls-publish --sls-publish-dry-run ::
```

### sls-lock

Generates `product-dependencies.lock` from `sls_product_dependency` targets.

```bash
pants sls-lock ::
# Generated lock file: dist/my-service/deployment/product-dependencies.lock (com.example:my-service, 2 dependencies)
```

For full goal reference see [reference/goals-reference.md](reference/goals-reference.md).

## Health Checks

Three mutually exclusive modes:

### check_args (Palantir pattern)

Same PEX binary, different arguments. Generates `service/bin/launcher-check.yml`.

```python
sls_service(
    ...,
    check_args=["--check"],
)
```

The launcher binary runs `python-service-launcher --check` which reads `launcher-check.yml`.

### check_command

Custom command string. Generates `service/monitoring/bin/check.sh`.

```python
sls_service(
    ...,
    check_command="python -m myservice.healthcheck",
)
```

### check_script

Developer-provided script copied verbatim to `service/monitoring/bin/check.sh`.

```python
sls_service(
    ...,
    check_script="scripts/my-check.sh",
)
```

## Hook Init System

When `hooks` is set, the hook init system is automatically enabled. The Dockerfile entrypoint switches from `service/bin/init.sh start` to `service/bin/entrypoint.sh`.

```python
sls_service(
    ...,
    hooks={
        "pre-configure.d/10-setup.sh": "scripts/setup.sh",
        "configure.d/20-config.sh": "scripts/configure.sh",
        "pre-startup.d/30-migrate.sh": "scripts/migrate.sh",
        "startup.d/40-warmup.sh": "scripts/warmup.sh",
    },
)
```

Lifecycle phases: `pre-configure.d` -> `configure.d` -> `pre-startup.d` -> `startup.d` -> `post-startup.d` -> `pre-shutdown.d` -> `shutdown.d`

## Subsystem Config

### [sls-distribution]

| Option | Default | Description |
|--------|---------|-------------|
| `default_python_version` | `"3.11"` | Default Python version |
| `default_command` | `"uvicorn"` | Default service command |
| `docker_base_image` | `"python:3.11-slim"` | Base Docker image |
| `docker_registry` | `""` | Docker registry URL |
| `apollo_hub_url` | `""` | Apollo Hub URL |
| `apollo_auth_token` | `""` | Apollo Hub bearer token |
| `publish_channel` | `""` | Override publish channel (empty = auto-detect) |
| `install_path` | `"/opt/services"` | Container install path |
| `manifest_version` | `"1.0"` | Manifest version string |
| `strict_validation` | `True` | Enable strict validation |

### [python-service-launcher]

| Option | Default | Description |
|--------|---------|-------------|
| `version` | `"v0.1.0"` | GitHub release tag |
| `github_repo` | `"jaymd96/python-service-launcher"` | GitHub owner/repo |
| `known_versions` | (4 platform entries) | `"version\|os\|arch\|sha256\|size"` entries |

## Complete BUILD Example

```python
# BUILD

sls_product_dependency(
    name="database-dep",
    product_group="com.example",
    product_name="sample-database",
    minimum_version="1.0.0",
    maximum_version="2.0.0",
)

sls_product_incompatibility(
    name="legacy-incompat",
    product_group="com.example",
    product_name="legacy-service",
    version_range="< 2.0.0",
    reason="Incompatible API endpoints",
)

sls_service(
    name="my-service",
    product_group="com.example",
    product_name="my-service",
    version="1.0.0",
    entrypoint="app:app",
    command="uvicorn",
    args=["--host", "0.0.0.0", "--port", "8080"],
    check_args=["--check"],
    hooks={
        "pre-startup.d/10-migrate.sh": "scripts/migrate.sh",
    },
    product_dependencies=[":database-dep"],
    product_incompatibilities=[":legacy-incompat"],
    resource_requests={"cpu": "100m", "memory": "256Mi"},
    resource_limits={"cpu": "500m", "memory": "512Mi"},
    labels={"team": "platform"},
)
```

## Dev & Testing

```bash
hatch run test          # Run test suite
hatch run lint          # Check code quality
hatch build             # Build wheel
```

Tests use Pants `RuleRunner` for isolated rule testing:

```python
from pants.testutil.rule_runner import RuleRunner, QueryRule

@pytest.fixture
def rule_runner():
    return RuleRunner(
        rules=[*all_rules(), QueryRule(SlsManifest, [SlsManifestRequest])],
        target_types=[SlsServiceTarget, SlsProductDependencyTarget],
    )
```

## Installing Skills via pants-claude-plugins

This plugin ships a `bundled_claude_plugins.py` module (at `src/pants_sls_distribution/bundled_claude_plugins.py`) that automatically delivers all 4 deployment pipeline skills to consuming projects.

**Setup**: Add both backends to `pants.toml`:

```toml
[GLOBAL]
backend_packages = [
    "pants_sls_distribution",
    "pants_claude_plugins",
]
```

**Install**: All 4 skills arrive with one command:

```bash
pants claude-install --include-bundled ::
```

This installs:
- `sls-distribution` -- Pants goals, targets, BUILD syntax
- `docker-generator` -- Dockerfile generation API
- `release-hub` -- Release publishing and version detection
- `service-launcher` -- Go launcher configuration and memory management

For finer-grained control, declare individual skills as `claude_plugin()` targets in BUILD files instead.

## Gotchas

- **EntrypointField filtering**: Goals filter targets using `t.has_field(EntrypointField)` to find `sls_service` targets. This uses a field unique to `sls_service`, not a shared field like `ProductGroupField` (which is also on `sls_product_dependency`).
- **camelCase YAML keys**: The generated `launcher-static.yml` uses camelCase keys (`configType`, `launchMode`, `maxRssPercent`) matching Go struct tags in python-service-launcher.
- **Health check mutual exclusivity**: `check_args`, `check_command`, and `check_script` are mutually exclusive. Setting more than one should trigger a validation error.
- **Hook init auto-detection**: Setting any value in the `hooks` field automatically enables `use_hook_init=True` in the generated Dockerfile and switches the entrypoint.
- **Launcher binaries**: The plugin downloads all 4 platform binaries (darwin/amd64, darwin/arm64, linux/amd64, linux/arm64) and bundles them all into the tarball, regardless of the build host platform.
- **Dry run**: `pants sls-publish --sls-publish-dry-run` uses the `PublishRequest.dry_run` flag -- no HTTP request is made.
