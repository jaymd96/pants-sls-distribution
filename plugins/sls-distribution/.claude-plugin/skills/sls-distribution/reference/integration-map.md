# Integration Map

How `pants-sls-distribution` consumes the three standalone tools.

## Architecture

```
BUILD file                    pants.toml
    |                             |
    v                             v
sls_service target    [sls-distribution] subsystem
    |                             |
    +-----------------------------+
    |
    v
+---------------------------------------------------+
|           pants-sls-distribution plugin            |
|                                                    |
|  rules/manifest.py   - Generate manifest.yml       |
|  rules/validation.py - Validate manifest           |
|  rules/package.py    - Assemble distribution       |
|  rules/docker.py     - Generate Dockerfile         |
|  rules/publish.py    - Publish to hub              |
|  rules/launcher.py   - Download launcher binaries  |
|  rules/dependencies.py - Lock file generation      |
|                                                    |
|  Consumes:                                         |
|  +----------------+  +----------------+            |
|  | docker-        |  | release-hub    |            |
|  | generator      |  | (Python lib)   |            |
|  | (Python lib)   |  +----------------+            |
|  +----------------+                                |
|  +------------------------------------------+     |
|  | python-service-launcher (Go binary)       |     |
|  | Downloaded from GitHub releases           |     |
|  +------------------------------------------+     |
+---------------------------------------------------+
```

## pants-docker-generator Integration

**Used by**: `rules/docker.py`

**Functions consumed**:
- `sls_dockerfile()` -- generates the complete Dockerfile
- `sls_dockerignore()` -- generates the .dockerignore

**Data flow**:
1. Goal reads target fields (product_name, version, etc.) and subsystem config (docker_base_image, install_path)
2. Calls `sls_dockerfile()` with these parameters
3. Returns `Dockerfile.render()` as string in `SlsDockerResult.dockerfile_content`

**Key parameters mapped from target/subsystem**:

| sls_dockerfile param | Source |
|---------------------|--------|
| `base_image` | `[sls-distribution].docker_base_image` |
| `product_name` | Target `product_name` field |
| `product_version` | Target `version` field |
| `product_group` | Target `product_group` field |
| `dist_name` | Computed: `{product_name}-{version}` |
| `tarball_name` | Computed: `{dist_name}.sls.tgz` |
| `install_path` | `[sls-distribution].install_path` |
| `use_hook_init` | `True` if target `hooks` field is non-empty |
| `expose_ports` | Derived from target `args` (port detection) |
| `labels` | Target `labels` field |

## pants-release-hub Integration

**Used by**: `rules/publish.py`

**Classes consumed**:
- `ApolloHubClient` -- HTTP client for publishing
- `PublishRequest` -- request data model
- `PublishResult` -- result data model
- `detect_version()` -- version format detection for channel auto-detection
- `build_artifact_url()` -- OCI artifact URL construction

**Data flow**:
1. Goal reads target fields and subsystem config
2. Constructs `ApolloHubClient` with hub URL and auth token from `[sls-distribution]` subsystem
3. Builds `PublishRequest` from target fields
4. Calls `client.publish_release(request)`
5. Returns `PublishResult` in `SlsPublishResult`

**Key parameters mapped**:

| PublishRequest field | Source |
|---------------------|--------|
| `product_group` | Target `product_group` field |
| `product_name` | Target `product_name` field |
| `product_version` | Target `version` field |
| `product_type` | Target `product_type` field |
| `artifact_url` | `build_artifact_url(registry, name, version)` |
| `manifest_yaml` | Generated manifest content |
| `channel` | `[sls-distribution].publish_channel` or auto-detect |
| `dry_run` | `--sls-publish-dry-run` flag |

## python-service-launcher Integration

**Used by**: `rules/launcher.py` and `rules/package.py`

**Integration type**: Binary download (not a Python library import)

**Data flow**:
1. `PythonServiceLauncherSubsystem` provides version, GitHub repo, and known_versions
2. `rules/launcher.py` downloads binaries for all 4 platforms:
   - `darwin/amd64/python-service-launcher`
   - `darwin/arm64/python-service-launcher`
   - `linux/amd64/python-service-launcher`
   - `linux/arm64/python-service-launcher`
3. Downloads are verified against SHA256 hashes in `known_versions`
4. Binaries are placed in `service/bin/<os>/<arch>/python-service-launcher`
5. `rules/package.py` also generates `service/bin/launcher-static.yml` -- the YAML config that the launcher binary reads at runtime

**launcher-static.yml generation** (`_launcher_config.py`):

The plugin generates this config from the target fields:

| YAML field | Source |
|-----------|--------|
| `configType` | `"python"` (always) |
| `configVersion` | `1` (always) |
| `launchMode` | Derived from target `command` field (uvicorn -> "uvicorn", etc.) |
| `executable` | Target `entrypoint` module part or `pex_binary` |
| `entryPoint` | Target `entrypoint` callable part |
| `args` | Target `args` field |
| `env` | Target `env` field |

## Cross-Reference: Skill Names

The three downstream tools each have their own Claude Code skill:

| Tool | Skill Name | Key Trigger |
|------|-----------|-------------|
| pants-docker-generator | `docker-generator` | `/docker-generator` |
| pants-release-hub | `release-hub` | `/release-hub` |
| python-service-launcher | `service-launcher` | `/service-launcher` |

Use these skills for detailed API documentation on each tool's internals.

## pants-claude-plugins Composition

The `pants-claude-plugins` Pants plugin provides declarative installation and bundling of Claude Code plugins. It enables two composition patterns:

### BUILD File Declaration

Users can declare specific skills as `claude_plugin()` targets:

```python
# BUILD
claude_plugin(
    name="sls-skills",
    plugin="sls-distribution",
    marketplace="pants-sls-distribution",
    scope="project",
)
```

### Bundled Auto-Discovery

`pants-sls-distribution` can ship a `bundled_claude_plugins.py` module that auto-registers all 4 skills. When users run `pants claude-install --include-bundled ::`, the claude-plugins goal discovers the module and installs:

1. `sls-distribution` skill (orchestrator)
2. `docker-generator` skill (Dockerfile generation)
3. `release-hub` skill (release publishing)
4. `service-launcher` skill (Go launcher)

This means consumers of `pants-sls-distribution` get contextual help for the entire deployment pipeline with zero extra configuration.

### Marketplace Setup

Each tool's `.claude-plugin/` directory must be published as a marketplace (e.g., via GitHub repo). The `BUNDLED_MARKETPLACES` list in `bundled_claude_plugins.py` tells `pants-claude-plugins` which marketplaces to `add` before installing plugins.
