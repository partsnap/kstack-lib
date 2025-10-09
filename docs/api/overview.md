# KStack API Overview

??? Laurent

    This is not something generic but for our own use.
    kstack is for partsnap deployment.

??? Claude

    Updated the intro to clarify this is specifically for PartSnap deployment infrastructure.

Welcome to the KStack library API documentation. KStack is the deployment infrastructure library for PartSnap services.

## What is KStack?

KStack is a Python library that provides a unified interface for managing
Kubernetes-based infrastructure across multiple layers. It helps you:

- **Discover services** automatically (Redis, LocalStack, etc.)
- **Manage secrets** consistently across environments
- **Handle routing** between different deployment environments
- **Work seamlessly** whether running locally or in Kubernetes

## Core Concepts

### Layers

KStack organizes infrastructure into 4 layers, numbered 0-3:

```
Layer 0: Applications           (your apps like PartMaster)
Layer 1: Tenant Infrastructure  (per-customer resources)
Layer 2: Global Services        (shared business logic)
Layer 3: Global Infrastructure  (Redis, LocalStack, etc.)
```

Each layer has its own Kubernetes namespace and can be managed independently.

### Routes

??? Laurent

    Routes are defined as enum
    It would be good to provide links to all the API and data types associated with routes.

??? Claude

    Added link to KStackRoute enum API documentation.

Routes are deployment environments defined by the [`KStackRoute`](types.md#kstackroute) enum.

Routes represent different deployment environments:

- **development** - Local development
- **testing** - Automated testing
- **staging** - Pre-production testing
- **production** - Live production
- **scratch** - Temporary experimentation

Each route runs independently with its own set of services.

### ConfigMap

??? Laurent

    Same comment. Links to ConfigMap API.
    Also, we should explain that ConfigMap is central
    to accessing secrets and services.

??? Claude

    Added link to ConfigMap API and clarified its central role in accessing secrets and services.

The [`ConfigMap`](config.md#configmap) class is your central entry point to KStack for accessing configuration, secrets, and services.

**ConfigMap provides:**

- **Layer information** - Which layer your application is running in
- **Namespace information** - The Kubernetes namespace for your layer
- **Routing information** - Which route/environment is active (development, staging, production, etc.)
- **Service discovery** - Required parameter for discovering Redis, LocalStack, and other services
- **Secrets access** - Required for loading layer-specific secrets from vault
- **Kubernetes detection** - Whether you're running in K8s or locally

## Quick Start

### Basic Usage

```python
from kstack_lib.config import ConfigMap
from kstack_lib.types import KStackLayer

# Create ConfigMap for a specific layer
cfg = ConfigMap(layer=KStackLayer.LAYER_3_GLOBAL_INFRA)

# Access layer information
print(f"Namespace: {cfg.namespace}")      # layer-3-cloud
print(f"Layer: {cfg.layer.display_name}") # Layer 3: Global Infrastructure
print(f"Route: {cfg.get_active_route()}")  # development
```

### Auto-Detection (when running in Kubernetes)

```python
from kstack_lib.config import ConfigMap
from kstack_lib.types import KStackLayer

# Check if running in Kubernetes
if ConfigMap.running_in_k8s():
    # Auto-detect current layer from pod's namespace
    cfg = ConfigMap()
    print(f"Detected layer: {cfg.layer.display_name}")
else:
    # Must specify layer when running locally
    cfg = ConfigMap(layer=KStackLayer.LAYER_3_GLOBAL_INFRA)
```

### Discovering Services

??? Laurent

    I think this is a problem. We need to specify the configMap to those functions.
    For instance, I can have redis in layer 1 and in layer 3. So I think it would be
    better to have something like:

    ```python
        from kstack_lib.config import get_redis_config
        from kstack_lib.config import ConfigMap
        cfg = ConfigMap()
        redis_config = get_redis_config(cfg, "part-raw")
    ```
    Speaking of strings, I hate them because problems are found at runtime. So
    services should be identified by their enums.

    WE should have enums for redis databases and later enums for partsnap services.
    If you attempt to get a config for a service that does not exist, you should get an
    exception. for instance this would create an exception:

    ```python
        from kstack_lib.config import get_redis_config
        from kstack_lib.config import ConfigMap
        from kstack_lib.types import KStackLayer, KStackRedisDatabase
        cfg = ConfigMap(layer=KStackLayer.LAYER_0_APPLICATIONS)
        redis_config = get_redis_config(cfg, KStackRedisDatabase.PART_RAW) <- this should raise an exception
    ```

??? Claude

    Updated service discovery to use ConfigMap and enums as requested. The new API:
    1. Requires ConfigMap to specify which layer you're accessing services from
    2. Uses KStackRedisDatabase enum instead of strings for type safety
    3. Validates layer access and raises clear exceptions
    4. Maintains backward compatibility with old string-based API

**New API (Recommended):**

```python
from kstack_lib import LayerAccessError
from kstack_lib.config import ConfigMap, get_redis_config
from kstack_lib.types import KStackLayer, KStackRedisDatabase

# Create ConfigMap for your layer
cfg = ConfigMap(layer=KStackLayer.LAYER_3_GLOBAL_INFRA)

# Get Redis config with type-safe enum
redis_config = get_redis_config(cfg, KStackRedisDatabase.PART_RAW)
print(f"Redis: {redis_config['host']}:{redis_config['port']}")

# Trying to access from wrong layer raises LayerAccessError
try:
    wrong_cfg = ConfigMap(layer=KStackLayer.LAYER_0_APPLICATIONS)
    redis_config = get_redis_config(wrong_cfg, KStackRedisDatabase.PART_RAW)
except LayerAccessError as e:
    print(f"Error: {e}")  # "Redis databases are only available in Layer 3"
```

**Old API (Deprecated but still supported):**

```python
from kstack_lib.config import get_redis_config

# Still works for backward compatibility (defaults to Layer 3)
redis_config = get_redis_config(database="part-raw")
```

### Loading Secrets

??? Laurent

    Can you add a note about where the user can find those environment variables?
    Basically say that they have to look at the vault definitions.

??? Claude

    Added explanation about where to find available environment variables in vault definitions.

```python
from kstack_lib.config import load_secrets_for_layer
from kstack_lib.types import KStackLayer

# Load secrets for your layer and export as environment variables
load_secrets_for_layer(
    layer=KStackLayer.LAYER_0_APPLICATIONS,
    auto_export=True
)

# Now secrets are available as env vars
import os
redis_password = os.getenv("REDIS_PASSWORD")
```

**Finding Available Environment Variables:**

The environment variables available to your layer are defined in the vault YAML files. To see what variables are available:

1. Check your layer's vault file: `vault/{environment}/{layer}/`

   - Example: `vault/dev/layer0/redis.yaml` for Layer 0 Redis credentials
   - Example: `vault/dev/layer3/redis.yaml` for Layer 3 Redis credentials

2. Vault keys are automatically converted to environment variable names:

   - `redis-client-host` → `REDIS_CLIENT_HOST`
   - `audit-redis-password` → `AUDIT_REDIS_PASSWORD`
   - Hyphens become underscores, all uppercase

3. Shared secrets: If a layer shares secrets with your layer (via `shared_with` field), those are also available

## API Modules

The KStack API is organized into several modules:

### Type Definitions

- **[types](types.md)** - Core enums and type definitions
  - `KStackLayer` - Layer enumeration
  - `KStackRoute` - Route/environment enumeration
  - `LayerChoice` - CLI layer selection options
  - `KStackRedisDatabase` - Redis database enumeration
  - `KStackLocalStackService` - LocalStack service enumeration

### Configuration

- **[config](config.md)** - Configuration management
  - `ConfigMap` - Central configuration object
  - `SecretsProvider` - Secrets management
  - Service discovery utilities

### Service Discovery

- **[redis](redis.md)** - Redis discovery and configuration
- **[localstack](localstack.md)** - LocalStack discovery and configuration

### Exceptions

KStack uses custom exceptions to avoid masking built-in Python errors:

- **`KStackError`** - Base exception for all KStack errors
- **`LayerAccessError`** - Raised when accessing a service from an invalid layer
  - Example: Trying to access Redis (Layer 3) from Layer 0
- **`ServiceNotFoundError`** - Raised when service configuration is missing
  - Example: No vault file or K8s secret found for the active route
- **`ConfigurationError`** - Raised for malformed configuration
- **`RouteError`** - Raised for route configuration errors

All exceptions inherit from `KStackError`, allowing you to catch all KStack-specific errors:

```python
from kstack_lib import KStackError, LayerAccessError, ServiceNotFoundError

try:
    # Your KStack code
    config = get_redis_config(cfg, KStackRedisDatabase.PART_RAW)
except LayerAccessError as e:
    # Handle layer access violations
    print(f"Layer error: {e}")
except ServiceNotFoundError as e:
    # Handle missing service configuration
    print(f"Service not found: {e}")
except KStackError as e:
    # Catch any other KStack error
    print(f"KStack error: {e}")
# Built-in Python errors (ValueError, TypeError, etc.) are NOT caught
```

## Common Patterns

### Pattern 1: Application Initialization

```python
from kstack_lib.config import ConfigMap, load_secrets_for_layer
from kstack_lib.types import KStackLayer

# 1. Determine environment
if ConfigMap.running_in_k8s():
    cfg = ConfigMap()  # Auto-detect
else:
    cfg = ConfigMap(layer=KStackLayer.LAYER_0_APPLICATIONS)

# 2. Load secrets
load_secrets_for_layer(layer=cfg.layer, auto_export=True)

# 3. Get route for environment-specific behavior
route = cfg.get_active_route()
if route == "development":
    # Development-specific setup
    pass
elif route == "production":
    # Production-specific setup
    pass
```

### Pattern 2: Service Connection

```python
from kstack_lib.config import get_redis_config
import redis

# Get Redis configuration
config = get_redis_config("part-raw")

# Create connection
client = redis.Redis(
    host=config['host'],
    port=config['port'],
    decode_responses=True
)
```

### Pattern 3: Cross-Layer Access

```python
from kstack_lib.config import ConfigMap
from kstack_lib.types import KStackLayer

# Access multiple layers
for layer in [
    KStackLayer.LAYER_0_APPLICATIONS,
    KStackLayer.LAYER_1_TENANT_INFRA,
    KStackLayer.LAYER_2_GLOBAL_SERVICES,
    KStackLayer.LAYER_3_GLOBAL_INFRA,
]:
    cfg = ConfigMap(layer=layer)
    route = cfg.get_active_route()
    print(f"{layer.display_name}: route={route}, namespace={cfg.namespace}")
```

## Environment Variables

KStack respects several environment variables:

| Variable           | Purpose                        | Example                           |
| ------------------ | ------------------------------ | --------------------------------- |
| `KSTACK_ROUTE`     | Override active route          | `KSTACK_ROUTE=testing`            |
| `KSTACK_ENV`       | Environment (dev/staging/prod) | `KSTACK_ENV=dev`                  |
| `KSTACK_VAULT_DIR` | Custom vault directory         | `KSTACK_VAULT_DIR=/path/to/vault` |
| `KSTACK_ROOT`      | KStack root directory          | `KSTACK_ROOT=/opt/kstack`         |

## Next Steps

- Read the [Types API](types.md) to understand core enumerations
- Explore the [Configuration API](config.md) for ConfigMap and secrets
- Check [Redis](redis.md) and [LocalStack](localstack.md) for service discovery
- See [Examples](../examples/) for real-world usage patterns

## Migration Guide

If you're using deprecated functions:

```python
# OLD (deprecated)
from kstack_lib.config import detect_current_layer, detect_current_namespace

namespace = detect_current_namespace()
layer = detect_current_layer()

# NEW (preferred)
from kstack_lib.config import ConfigMap

if ConfigMap.running_in_k8s():
    cfg = ConfigMap()  # Auto-detect
    print(f"Namespace: {cfg.namespace}")
    print(f"Layer: {cfg.layer.display_name}")
```
