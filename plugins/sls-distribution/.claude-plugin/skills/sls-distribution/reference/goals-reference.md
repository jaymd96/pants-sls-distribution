# Goals Reference

All goals filter targets using `t.has_field(EntrypointField)` to find `sls_service` targets.

## sls-manifest

**Goal class**: `SlsManifestGoal`
**Subsystem**: `SlsManifestGoalSubsystem` (name: `"sls-manifest"`)

Generates `deployment/manifest.yml` for each `sls_service` target.

```bash
pants sls-manifest ::
pants sls-manifest path/to/service:my-service
```

**Output**: `dist/<product-name>/deployment/manifest.yml`

**Rules chain**: `SlsManifestRequest` -> `SlsManifest`

The manifest contains product identity, version, dependencies, health check config, resource requirements, and custom extensions.

---

## sls-validate

**Goal class**: `SlsValidateGoal`
**Subsystem**: `SlsValidateGoalSubsystem` (name: `"sls-validate"`)

Validates generated manifests against schema and semantic rules.

```bash
pants sls-validate ::
```

**Output**:
```
PASS  com.example:my-service v1.0.0
All 1 manifest(s) valid.
```

Or on failure:
```
FAIL  com.example:my-service v1.0.0
  ERROR: product_name must start with lowercase letter
  WARN: no health check configured
```

**Rules chain**: `SlsManifestRequest` -> `SlsManifest` -> `SlsValidationRequest` -> `SlsValidationResult`

**Validation result fields**:
- `valid: bool`
- `errors: tuple[str, ...]` -- hard failures
- `warnings: tuple[str, ...]` -- advisory messages

---

## sls-package

**Goal class**: `SlsPackageGoal`
**Subsystem**: `SlsPackageGoalSubsystem` (name: `"sls-package"`)

Assembles the full SLS distribution layout and creates a `.sls.tgz` tarball.

```bash
pants sls-package ::
```

**Output**: `dist/<dist-name>.sls.tgz`

**Rules chain**: `SlsPackageRequest` -> `SlsPackageResult`

The result includes:
- `layout` -- directory structure with all files
- `launcher_digest` -- Pants Digest containing launcher binaries
- `manifest` -- the generated manifest

**Distribution layout**:
```
<dist-name>/
  deployment/
    manifest.yml
  service/
    bin/
      init.sh
      launcher-static.yml
      launcher-check.yml (if health check configured)
      darwin/
        amd64/python-service-launcher
        arm64/python-service-launcher
      linux/
        amd64/python-service-launcher
        arm64/python-service-launcher
    monitoring/
      bin/
        check.sh (if health check configured)
    lib/
      (PEX and Python artifacts)
  var/
    data/tmp/
    log/
    run/
    conf/
    state/
  hooks/ (if hook init enabled)
    entrypoint.sh
    hooks.sh
    pre-configure.d/
    configure.d/
    pre-startup.d/
    startup.d/
    post-startup.d/
    pre-shutdown.d/
    shutdown.d/
```

---

## sls-docker

**Goal class**: `SlsDockerGoal`
**Subsystem**: `SlsDockerGoalSubsystem` (name: `"sls-docker"`)

Generates a Dockerfile and .dockerignore using `pants-docker-generator`.

```bash
pants sls-docker ::
```

**Output**: `dist/<dist-name>/docker/Dockerfile` and `dist/<dist-name>/docker/.dockerignore`

If hook init is enabled, also writes `dist/<dist-name>/docker/hooks/entrypoint.sh` and `hooks.sh`.

**Rules chain**: `SlsDockerRequest` -> `SlsDockerResult`

**Result fields**:
- `dockerfile_content: str`
- `dockerignore_content: str`
- `hook_entrypoint_content: Optional[str]`
- `hook_library_content: Optional[str]`
- `package_result` -- references the packaging result for dist_name, etc.

Uses `pants_docker_generator.sls_dockerfile()` internally with parameters derived from the target fields and `[sls-distribution]` subsystem config.

---

## sls-publish

**Goal class**: `SlsPublishGoal`
**Subsystem**: `SlsPublishGoalSubsystem` (name: `"sls-publish"`)

Publishes releases to Apollo Hub using `pants-release-hub`.

```bash
pants sls-publish ::
pants sls-publish --sls-publish-dry-run ::
```

**Options**:
- `--sls-publish-dry-run` (bool, default: False) -- show what would be published

**Output**:
```
Published com.example:my-service v1.0.0: Published release abc123
  Release ID: abc123
```

**Rules chain**: `SlsPublishRequest` -> `SlsPublishResult`

Uses `pants_release_hub.ApolloHubClient` with:
- `base_url` from `[sls-distribution].apollo_hub_url`
- `auth_token` from `[sls-distribution].apollo_auth_token`
- Version detection via `detect_version()` for channel auto-detection

---

## sls-lock

**Goal class**: `SlsLockGoal`
**Subsystem**: `SlsLockGoalSubsystem` (name: `"sls-lock"`)

Generates `product-dependencies.lock` from `sls_product_dependency` targets referenced by `product_dependencies` field.

```bash
pants sls-lock ::
```

**Output**: `dist/<product-name>/deployment/product-dependencies.lock`

Skips targets with no dependencies.

**Rules chain**: `SlsLockFileRequest` -> `SlsLockFileResult`

**Result fields**:
- `content: str` -- lock file content
- `product_id: str`
- `dependency_count: int`
