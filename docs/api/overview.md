# KStack API Overview

Welcome to the KStack library API documentation. This guide will help you understand how to use KStack to build
cloud-native applications that work seamlessly across different environments.

??? Laurent This is not something generic but for our own use.

    kstack is for partsnap deployment.

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

??? Laurent Routes are defined as enum

    If would be good to provide links to all the API and data types associated with routes.

Routes represent different deployment environments:

- **development** - Local development
- **testing** - Automated testing
- **staging** - Pre-production testing
- **production** - Live production
- **scratch** - Temporary experimentation

Each route runs independently with its own set of services.

### ConfigMap

??? Laurent Same comment. Links to ConfigMap API.

    Also, we should should

The `ConfigMap` class is your central entry point to KStack. It provides:

- Layer information (which layer you're in)
- Namespace information (which Kubernetes namespace)
- Routing information (which route/environment is active)
- Kubernetes detection (are you running in K8s?)

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

```python
from kstack_lib.config import get_redis_config, get_localstack_config

# Get Redis connection info
redis_config = get_redis_config("part-raw")
print(f"Redis: {redis_config['host']}:{redis_config['port']}")

# Get LocalStack endpoint
localstack_config = get_localstack_config()
print(f"LocalStack: {localstack_config['endpoint_url']}")
```

### Loading Secrets

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

## API Modules

The KStack API is organized into several modules:

### Type Definitions

- **[types](types.md)** - Core enums and type definitions
  - `KStackLayer` - Layer enumeration
  - `KStackRoute` - Route/environment enumeration
  - `LayerChoice` - CLI layer selection options

### Configuration

- **[config](config.md)** - Configuration management
  - `ConfigMap` - Central configuration object
  - `SecretsProvider` - Secrets management
  - Service discovery utilities

### Service Discovery

- **[redis](redis.md)** - Redis discovery and configuration
- **[localstack](localstack.md)** - LocalStack discovery and configuration

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
