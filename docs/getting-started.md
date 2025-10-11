# Getting Started with KStack-lib

This guide will help you get up and running with kstack-lib in your PartSnap services.

## Installation

Add kstack-lib to your project:

```bash
uv add kstack-lib
```

## Basic Concepts

### Context-Aware Design

KStack-lib automatically detects whether you're running:

- **Locally**: On a development machine (uses vault files, local configs)
- **In-Cluster**: Inside a Kubernetes pod (uses ConfigMaps and Secrets)

You don't need to configure anything - the library detects the context automatically.

### Three-Tier Architecture

```
kstack_lib/
├── any/          # Shared code (protocols, types, container)
├── local/        # Local development adapters
└── cluster/      # Production K8s adapters
```

The IoC container selects the right adapter at runtime.

## Common Use Cases

### 1. Detect Current Environment

```python
from kstack_lib.any.container import get_environment_detector

detector = get_environment_detector()
environment = detector.get_environment()  # "development", "staging", or "production"

print(f"Running in {environment}")
```

### 2. Access Cloud Storage

The Cloud Abstraction Layer (CAL) provides a unified interface for cloud storage:

```python
from pathlib import Path
from kstack_lib.cal import CloudContainer
from kstack_lib.config import ConfigMap
from kstack_lib.types import KStackLayer, KStackEnvironment

# Create configuration
cfg = ConfigMap(
    layer=KStackLayer.LAYER_3_GLOBAL_INFRA,
    environment=KStackEnvironment.DEVELOPMENT,
)

# Use CloudContainer with context manager
with CloudContainer(
    cfg=cfg,
    config_root=Path("./config"),
    vault_root=Path("./vault"),
) as cloud:
    # Get object storage service (automatically uses LocalStack locally, S3 in cluster)
    storage = cloud.object_storage()

    # Create bucket
    storage.create_bucket("my-bucket")

    # Upload a file
    with open("data.json", "rb") as f:
        storage.upload_object(
            bucket="my-bucket",
            key="path/to/file.json",
            file_obj=f,
            content_type="application/json"
        )

    # Download a file
    data = storage.download_object(
        bucket="my-bucket",
        key="path/to/file.json"
    )

    # List objects
    objects = storage.list_objects(
        bucket="my-bucket",
        prefix="path/to/"
    )
    for obj in objects:
        print(f"{obj['Key']}: {obj['Size']} bytes")
```

### 3. Use ConfigMap

ConfigMap provides structured access to layer and environment configuration:

```python
from kstack_lib.config import ConfigMap
from kstack_lib.types import KStackLayer, KStackEnvironment

# Create configuration map
cfg = ConfigMap(
    layer=KStackLayer.LAYER_3_GLOBAL_INFRA,
    environment=KStackEnvironment.DEVELOPMENT,
)

# Access properties
print(f"Layer: {cfg.layer.display_name}")
print(f"Environment: {cfg.environment.value}")
print(f"Namespace: {cfg.namespace}")

# Get active route
route = cfg.get_active_route()
print(f"Active route: {route}")

# Read ConfigMap values (in cluster)
value = cfg.get_value("configmap-name", "key")
```

### 4. Access Secrets

```python
from kstack_lib.any.container import get_secrets_provider

# Get secrets provider (vault locally, K8s Secrets in cluster)
secrets = get_secrets_provider()

# Get service credentials
creds = secrets.get_credentials(
    service="s3",
    layer="layer3",
    environment="development"
)

# Access credentials
aws_access_key = creds["aws_access_key_id"]
aws_secret_key = creds["aws_secret_access_key"]
```

## Development Workflow

### Local Development Setup

1. **Ensure vault is decrypted** (kstack-lib will use vault files):

```bash
partsecrets reveal --team dev
```

2. **Set environment variables** (optional, for testing):

```bash
export KSTACK_ENVIRONMENT=development
```

3. **Run your service**:

```python
from pathlib import Path
from kstack_lib.any.container import get_environment_detector
from kstack_lib.cal import CloudContainer
from kstack_lib.config import ConfigMap
from kstack_lib.types import KStackLayer, KStackEnvironment

# Automatically uses local adapters
detector = get_environment_detector()
print(f"Environment: {detector.get_environment()}")  # "development"

# Storage automatically uses LocalStack at http://localhost:4566
cfg = ConfigMap(
    layer=KStackLayer.LAYER_3_GLOBAL_INFRA,
    environment=KStackEnvironment.DEVELOPMENT,
)

with CloudContainer(cfg, config_root=Path("./config"), vault_root=Path("./vault")) as cloud:
    storage = cloud.object_storage()
    buckets = storage.list_buckets()
    print(f"Buckets: {buckets}")
```

### Cluster Deployment

When deployed to Kubernetes:

1. **ConfigMaps** provide configuration
2. **Secrets** provide credentials
3. **Service Account** provides namespace/environment detection

No code changes needed - kstack-lib detects the cluster context automatically.

## Type System

KStack-lib provides comprehensive types for infrastructure:

```python
from kstack_lib.types import KStackLayer, KStackEnvironment, KStackRedisDatabase

# Layers
layer = KStackLayer.LAYER_3_GLOBAL_INFRA

# Environments
env = KStackEnvironment.DEVELOPMENT

# Redis databases
database = KStackRedisDatabase.PART_RAW
```

See [API Reference: Types](api/types.md) for complete documentation.

## Error Handling

KStack-lib uses custom exceptions for different error scenarios:

```python
from pathlib import Path
from kstack_lib.any.exceptions import (
    KStackError,  # Base exception
    KStackConfigurationError,  # Config issues
    KStackServiceNotFoundError,  # Service not available
    KStackEnvironmentError,  # Wrong context
)
from kstack_lib.cal import CloudContainer
from kstack_lib.config import ConfigMap
from kstack_lib.types import KStackLayer, KStackEnvironment

try:
    cfg = ConfigMap(
        layer=KStackLayer.LAYER_3_GLOBAL_INFRA,
        environment=KStackEnvironment.DEVELOPMENT,
    )
    with CloudContainer(cfg, config_root=Path("./config"), vault_root=Path("./vault")) as cloud:
        storage = cloud.object_storage()
        storage.upload_object("my-bucket", "file.json", file_obj=data)
except KStackServiceNotFoundError:
    print("S3 service not configured")
except KStackConfigurationError as e:
    print(f"Configuration error: {e}")
```

## Next Steps

- Learn about the [IoC Container](architecture/ioc-container.md)
- Explore the [Cloud Abstraction Layer](architecture/cal-architecture.md)
- Read the [Architecture Overview](architecture/README.md)
