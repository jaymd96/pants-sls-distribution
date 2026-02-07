# Targets Reference

## sls_service

Primary target for Python services packaged as SLS distributions.

### Identity Fields (required)

| Field | Type | Required | Default | Description |
|-------|------|----------|---------|-------------|
| `product_group` | `str` | Yes | -- | Maven-style group ID (e.g., `com.example`) |
| `product_name` | `str` | Yes | -- | Product name (e.g., `my-service`) |
| `version` | `str` | Yes | -- | SLS orderable version (X.Y.Z, X.Y.Z-rcN, etc.) |
| `entrypoint` | `str` | Yes | -- | Python entrypoint as `module:callable` |

### Identity Fields (optional)

| Field | Type | Default | Description |
|-------|------|---------|-------------|
| `product_type` | `str` | `"helm.v1"` | SLS product type: helm.v1, asset.v1, service.v1 |
| `display_name` | `str` | None | Human-readable name |
| `description` | `str` | None | Product description |

### Service Configuration

| Field | Type | Default | Description |
|-------|------|---------|-------------|
| `command` | `str` | `"uvicorn"` | Launch command |
| `args` | `tuple[str]` | `("--host", "0.0.0.0", "--port", "8080")` | Service arguments |
| `python_version` | `str` | `"3.11"` | Python version requirement |
| `env` | `dict[str, str]` | `{}` | Environment variables |
| `pex_binary` | `str` | None | PEX binary path (uses pex launch mode instead of command) |
| `hooks` | `dict[str, str]` | `{}` | Hook scripts: `phase.d/script.sh` -> source path |

### Health Checks (mutually exclusive)

| Field | Type | Default | Description |
|-------|------|---------|-------------|
| `check_args` | `tuple[str]` | None | Args for same-PEX health check |
| `check_command` | `str` | None | Custom health check command |
| `check_script` | `str` | None | Path to custom check.sh script |

### Resources

| Field | Type | Default | Description |
|-------|------|---------|-------------|
| `resource_requests` | `dict[str, str]` | `{}` | K8s resource requests |
| `resource_limits` | `dict[str, str]` | `{}` | K8s resource limits |
| `replication_desired` | `int` | None | Desired replicas |
| `replication_min` | `int` | None | Minimum replicas |
| `replication_max` | `int` | None | Maximum replicas |

### Metadata

| Field | Type | Default | Description |
|-------|------|---------|-------------|
| `labels` | `dict[str, str]` | `{}` | Product labels |
| `annotations` | `dict[str, str]` | `{}` | Product annotations |
| `traits` | `tuple[str]` | `()` | Capability traits |
| `manifest_extensions` | `dict[str, str]` | `{}` | Additional manifest fields |

### Dependencies

| Field | Type | Default | Description |
|-------|------|---------|-------------|
| `product_dependencies` | `SpecialCasedDependencies` | `()` | Refs to `sls_product_dependency` targets |
| `product_incompatibilities` | `SpecialCasedDependencies` | `()` | Refs to `sls_product_incompatibility` targets |
| `artifacts` | `SpecialCasedDependencies` | `()` | Refs to `sls_artifact` targets |

### Sources

| Field | Type | Default | Description |
|-------|------|---------|-------------|
| `sources` | `MultipleSourcesField` | `("**/*.py",)` | Python source files |

---

## sls_asset

Static file distribution without runtime.

| Field | Type | Required | Default | Description |
|-------|------|----------|---------|-------------|
| `product_group` | `str` | Yes | -- | Group ID |
| `product_name` | `str` | Yes | -- | Product name |
| `version` | `str` | Yes | -- | Version |
| `product_type` | `str` | No | `"helm.v1"` | Product type (usually `"asset.v1"`) |
| `assets` | `dict[str, str]` | No | `{}` | Source -> destination mapping |
| `product_dependencies` | | No | `()` | Product dependency refs |
| `product_incompatibilities` | | No | `()` | Incompatibility refs |
| `artifacts` | | No | `()` | Artifact refs |
| `labels` | `dict[str, str]` | No | `{}` | Labels |
| `annotations` | `dict[str, str]` | No | `{}` | Annotations |
| `manifest_extensions` | `dict[str, str]` | No | `{}` | Manifest extensions |

---

## sls_product_dependency

| Field | Type | Required | Default | Description |
|-------|------|----------|---------|-------------|
| `product_group` | `str` | Yes | -- | Dependency group ID |
| `product_name` | `str` | Yes | -- | Dependency product name |
| `minimum_version` | `str` | Yes | -- | Minimum compatible version |
| `maximum_version` | `str` | No | None | Maximum compatible version |
| `recommended_version` | `str` | No | None | Recommended version |
| `optional` | `bool` | No | `False` | Whether dependency is optional |

---

## sls_product_incompatibility

| Field | Type | Required | Default | Description |
|-------|------|----------|---------|-------------|
| `product_group` | `str` | Yes | -- | Incompatible product group |
| `product_name` | `str` | Yes | -- | Incompatible product name |
| `version_range` | `str` | Yes | -- | Version range (e.g., `"< 2.0.0"`) |
| `reason` | `str` | Yes | -- | Explanation |

---

## sls_artifact

| Field | Type | Required | Default | Description |
|-------|------|----------|---------|-------------|
| `type` | `str` | No | `"oci"` | Artifact type |
| `uri` | `str` | Yes | -- | Artifact URI |
| `artifact_name` | `str` | No | None | Artifact name |
| `digest` | `str` | No | None | Content digest (e.g., sha256) |
