# Secrets Management

Unified secrets management for KStack applications with layer-based access control and cross-layer secret sharing.

## Overview

KStack provides a hierarchical secrets management system that:

- **Automatically discovers secrets** from vault (local development) or Kubernetes secrets (deployed mode)
- **Enforces layer-based access control** to prevent unauthorized cross-layer access
- **Supports cross-layer secret sharing** with explicit `shared_with` declarations
- **Exports secrets as environment variables** for seamless library integration
- **Works transparently** across local development and Kubernetes deployments

## Layer Architecture

KStack uses a 4-layer architecture:

- **Layer 0 (Application Services)**: User-facing applications (partfinder, partmaster)
- **Layer 1 (Redis Instances)**: Dedicated Redis instances per application
- **Layer 2 (Global Infrastructure)**: Shared infrastructure (Traefik, monitoring)
- **Layer 3 (Cloud Services)**: Cloud-managed services (Redis Cloud, RDS)

Each layer has its own secrets, and cross-layer access is controlled via `shared_with` policies.

## Quick Start

### Local Development

```python
from kstack_lib.config import load_secrets_for_layer

# Load all accessible secrets for Layer 0 and export as env vars
load_secrets_for_layer(layer="layer0", auto_export=True)

# Now environment variables are set (REDIS_CLIENT_HOST, AUDIT_REDIS_PASSWORD, etc.)
# Libraries like partsnap-rediscache can use them automatically
from partsnap_rediscache.config import RedisConfig
config = RedisConfig(prefix="audit")  # Will find AUDIT_REDIS_CLIENT_HOST, etc.
```

### Kubernetes Deployment

In Kubernetes, secrets are loaded automatically from the pod's namespace:

```python
from kstack_lib.config import load_secrets_for_layer

# Same code works in K8s - automatically reads from K8s Secrets
load_secrets_for_layer(layer="layer0", auto_export=True)
```

## Vault Directory Structure

Secrets are organized by environment and layer:

```
vault/
├── dev/                    # Development environment (also called "development")
│   ├── layer0/             # Application services secrets
│   │   ├── partfinder.yaml
│   │   └── partmaster.yaml
│   ├── layer1/             # Redis instance secrets
│   │   ├── redis-partfinder.yaml
│   │   └── redis-partmaster.yaml
│   ├── layer2/             # Global infrastructure secrets
│   │   └── traefik.yaml
│   └── layer3/             # Cloud service secrets
│       └── redis-cloud.yaml
├── staging/                # Staging environment
│   ├── layer0/
│   ├── layer1/
│   ├── layer2/
│   └── layer3/
└── production/             # Production environment
    ├── layer0/
    ├── layer1/
    ├── layer2/
    └── layer3/
```

## Vault File Format

### Basic Secrets File

```yaml
# vault/dev/layer1/redis-partmaster.yaml
redis-client-host: redis-partmaster.layer-1-development.svc.cluster.local
redis-client-port: 6379
redis-client-username: default
redis-password: layer1-dev-secret-123
```

### Cross-Layer Sharing

Secrets can be shared across layers using `shared_with`:

```yaml
# vault/dev/layer1/redis-partmaster.yaml
# Layer 1 Redis secrets accessible to Layer 0 applications
redis-client-host: redis-partmaster.layer-1-development.svc.cluster.local
redis-client-port: 6379
redis-password: layer1-dev-secret-456
shared_with:
  - layer0 # Allow Layer 0 applications to access these secrets
```

```yaml
# vault/dev/layer3/redis-cloud.yaml
# Layer 3 Redis Cloud secrets NOT accessible to other layers
redis-client-host: redis-14880.fcrce172.us-east-1-1.ec2.redns.redis-cloud.com
redis-client-port: 14880
redis-password: cloud-secret-789
# No shared_with - only Layer 3 can access
```

### Application-Specific Prefixes

Use hyphens to create prefixed environment variables:

```yaml
# vault/dev/layer1/redis-partmaster.yaml
# Standard Redis connection (REDIS_CLIENT_HOST, REDIS_PASSWORD, etc.)
redis-client-host: redis-partmaster.svc.cluster.local
redis-client-port: 6379
redis-password: main-db-secret

# Audit database with prefix (AUDIT_REDIS_CLIENT_HOST, AUDIT_REDIS_PASSWORD, etc.)
audit-redis-client-host: redis-audit.svc.cluster.local
audit-redis-client-port: 6379
audit-redis-password: audit-db-secret

shared_with:
  - layer0
```

Environment variables created:

- `REDIS_CLIENT_HOST` = `redis-partmaster.svc.cluster.local`
- `REDIS_CLIENT_PORT` = `6379`
- `REDIS_PASSWORD` = `main-db-secret`
- `AUDIT_REDIS_CLIENT_HOST` = `redis-audit.svc.cluster.local`
- `AUDIT_REDIS_CLIENT_PORT` = `6379`
- `AUDIT_REDIS_PASSWORD` = `audit-db-secret`

### Metadata Fields

Metadata fields are not exported as environment variables:

```yaml
# vault/dev/layer2/traefik.yaml
description: Traefik ingress controller credentials
created: 2025-01-15
status: active
migration: none

# Actual secrets (will be exported)
traefik-api-key: secret-key-123
traefik-dashboard-password: dashboard-secret-456

shared_with:
  - layer0
```

Metadata fields ignored during export:

- `shared_with`
- `description`
- `created`
- `status`
- `migration`

## Access Control Rules

### Same-Layer Access

Layers always have access to their own secrets:

```python
# Layer 0 application can always access Layer 0 secrets
load_secrets_for_layer("layer0")  # ✅ Returns all layer0/*.yaml secrets
```

### Cross-Layer Access

Cross-layer access requires explicit `shared_with` declaration:

```yaml
# vault/dev/layer1/redis-partmaster.yaml
redis-client-host: redis-partmaster.svc.cluster.local
redis-password: secret-123
shared_with:
  - layer0 # ✅ Layer 0 can access
  # ❌ Layer 2 and Layer 3 cannot access
```

```python
# Layer 0 application
load_secrets_for_layer("layer0")
# ✅ Returns: layer0/*.yaml + layer1/*.yaml (with shared_with: [layer0])

# Layer 2 application
load_secrets_for_layer("layer2")
# ✅ Returns: layer2/*.yaml only (layer1 secrets not shared with layer2)
```

## Environment Setup

### Local Development

1. **Set environment variables**:

   ```bash
   export KSTACK_ENV=development  # or "dev" (both work)
   ```

2. **Vault directory discovery** (in priority order):

   - `KSTACK_VAULT_DIR` environment variable
   - `${KSTACK_ROOT}/vault` (from `KSTACK_ROOT` env var)
   - `/home/lbrack/github/devops/kstack-lib/vault` (development convention)

3. **Load secrets in your application**:

   ```python
   from kstack_lib.config import load_secrets_for_layer

   # Auto-export secrets as environment variables
   load_secrets_for_layer("layer0", auto_export=True)
   ```

### Kubernetes Deployment

1. **Secrets are auto-deployed** by kstack CLI to appropriate namespaces

2. **Namespace detection** is automatic via `/var/run/secrets/kubernetes.io/serviceaccount/namespace`

3. **Secrets format** in Kubernetes:

   ```yaml
   apiVersion: v1
   kind: Secret
   metadata:
     name: layer0-secrets
     namespace: layer-0-partmaster # Application namespace
   type: Opaque
   data:
     redis-client-host: <base64>
     redis-client-port: <base64>
     redis-password: <base64>
   ```

4. **Same application code works**:

   ```python
   from kstack_lib.config import load_secrets_for_layer

   # Automatically reads from K8s Secret in current namespace
   load_secrets_for_layer("layer0", auto_export=True)
   ```

## Key Naming Conventions

Vault keys use **hyphens** and are automatically converted to **uppercase with underscores** for environment variables:

| Vault Key                 | Environment Variable      |
| ------------------------- | ------------------------- |
| `redis-client-host`       | `REDIS_CLIENT_HOST`       |
| `redis-password`          | `REDIS_PASSWORD`          |
| `audit-redis-client-host` | `AUDIT_REDIS_CLIENT_HOST` |
| `aws-access-key-id`       | `AWS_ACCESS_KEY_ID`       |
| `traefik-api-key`         | `TRAEFIK_API_KEY`         |

## API Usage

### Load and Export Secrets

```python
from kstack_lib.config import load_secrets_for_layer

# Load and auto-export as environment variables (recommended)
secrets = load_secrets_for_layer("layer0", auto_export=True)

# Load without exporting (manual control)
secrets = load_secrets_for_layer("layer0", auto_export=False)
print(secrets)
# {'redis-client-host': '...', 'redis-password': '...', ...}
```

### Advanced Usage with SecretsProvider

```python
from kstack_lib.config.secrets import SecretsProvider
from pathlib import Path

# Custom vault directory
provider = SecretsProvider(vault_dir=Path("/custom/vault"))

# Check if running in Kubernetes
if provider.is_running_in_k8s():
    secrets = provider.load_secrets_from_k8s("layer0")
else:
    secrets = provider.load_secrets_from_vault("layer0")

# Manual environment variable export
provider.export_as_env_vars(secrets, override_existing=False)
```

### Environment Variable Precedence

Existing environment variables take precedence over vault secrets:

```python
import os
from kstack_lib.config import load_secrets_for_layer

# Set an override before loading secrets
os.environ["REDIS_CLIENT_HOST"] = "override-redis.example.com"

# Load secrets (won't override existing env var)
load_secrets_for_layer("layer0", auto_export=True)

print(os.environ["REDIS_CLIENT_HOST"])
# Output: override-redis.example.com (from explicit env var, not vault)
```

To force vault values to override:

```python
from kstack_lib.config.secrets import SecretsProvider

provider = SecretsProvider()
secrets = provider.load_secrets("layer0")
provider.export_as_env_vars(secrets, override_existing=True)  # Force override
```

## Integration with partsnap-rediscache

The secrets system seamlessly integrates with `partsnap-rediscache`:

```python
from kstack_lib.config import load_secrets_for_layer
from partsnap_rediscache.config import RedisConfig

# Load Layer 0 secrets (includes shared Layer 1 Redis credentials)
load_secrets_for_layer("layer0", auto_export=True)

# RedisConfig automatically finds environment variables
config = RedisConfig()
# Looks for: REDIS_CLIENT_HOST, REDIS_CLIENT_PORT, REDIS_PASSWORD, etc.

# Application-specific prefix
audit_config = RedisConfig(prefix="audit")
# Looks for: AUDIT_REDIS_CLIENT_HOST, AUDIT_REDIS_CLIENT_PORT, etc.
```

## Best Practices

1. **Never commit vault files to git** - They're already in `.gitignore`

2. **Use explicit `shared_with` for cross-layer access**:

   ```yaml
   # ✅ Good - Explicit sharing
   shared_with: [layer0]
   # ❌ Bad - No sharing declaration (only same layer can access)
   ```

3. **Use consistent prefixes** for multi-database applications:

   ```yaml
   # Main database
   redis-client-host: redis-main.svc.cluster.local
   redis-password: main-secret

   # Audit database with "audit-" prefix
   audit-redis-client-host: redis-audit.svc.cluster.local
   audit-redis-password: audit-secret
   ```

4. **Rotate secrets regularly** in production environments

5. **Use separate environments** (dev, staging, production) with different secrets

6. **Test locally before deploying** to ensure vault files are correct

7. **Document secret purposes** using `description` metadata:
   ```yaml
   description: Redis credentials for partmaster application audit database
   created: 2025-01-15
   status: active
   ```

## Troubleshooting

### Secrets not found

```python
from kstack_lib.config import load_secrets_for_layer

secrets = load_secrets_for_layer("layer0")
print(secrets)  # Empty dict {}
```

**Solution**: Check environment and vault directory:

```python
from kstack_lib.config.secrets import SecretsProvider

provider = SecretsProvider()
print(f"Environment: {provider.get_current_environment()}")  # Should be "dev" or "development"
print(f"Vault directory: {provider.vault_dir}")
print(f"Running in K8s: {provider.is_running_in_k8s()}")
```

### Cross-layer access denied

Layer 0 cannot access Layer 1 secrets even though they should be shared.

**Solution**: Verify `shared_with` in vault file:

```yaml
# vault/dev/layer1/redis-partmaster.yaml
redis-client-host: redis.svc.cluster.local
shared_with:
  - layer0 # ✅ This line is required!
```

### Environment variables not set

```python
load_secrets_for_layer("layer0", auto_export=True)
print(os.environ.get("REDIS_CLIENT_HOST"))  # None
```

**Solution**: Check vault key naming:

```yaml
# ❌ Wrong - uses underscores
redis_client_host: redis.svc.cluster.local

# ✅ Correct - uses hyphens
redis-client-host: redis.svc.cluster.local
```

### Kubernetes namespace detection failing

```python
provider = SecretsProvider()
print(provider.get_current_namespace())  # None (but should be "layer-0-partmaster")
```

**Solution**: Ensure running in a proper K8s pod with service account mounted:

```bash
ls -la /var/run/secrets/kubernetes.io/serviceaccount/namespace
# Should exist in K8s pods
```

## See Also

- [Redis Client Guide](redis-client.md) - Using Redis clients with secrets
- [Configuration Discovery](configuration.md) - Understanding route and config discovery
- [API Reference - Secrets](../api/config.md#secrets-management) - Detailed API documentation
