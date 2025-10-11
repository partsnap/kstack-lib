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
from kstack_lib import get_environment_detector

detector = get_environment_detector()
environment = detector.get_environment()  # "development", "staging", or "production"

print(f"Running in {environment}")
```

### 2. Access Cloud Storage

The Cloud Abstraction Layer (CAL) provides a unified interface for cloud storage:

```python
from kstack_lib import get_cloud_storage_adapter

# Automatically uses S3 in cluster, LocalStack locally
storage = get_cloud_storage_adapter(service="s3")

# Upload a file
with open("data.json", "rb") as f:
    storage.upload_file(
        bucket="my-bucket",
        key="path/to/file.json",
        body=f
    )

# Download a file
response = storage.download_file(
    bucket="my-bucket",
    key="path/to/file.json"
)
data = response["Body"].read()

# List objects
objects = storage.list_objects(
    bucket="my-bucket",
    prefix="path/to/"
)
for obj in objects.get("Contents", []):
    print(obj["Key"])
```

### 3. Load Configuration

Configuration comes from different sources depending on context:

```python
from kstack_lib.config import get_config

# Loads from vault (local) or ConfigMap (cluster)
config = get_config(
    layer="layer3",
    environment="development",
    config_type="service"  # or "global"
)

# Access config values
database_url = config.get("database", {}).get("url")
```

### 4. Access Secrets

```python
from kstack_lib import get_secrets_provider

# Get secrets provider (vault locally, K8s Secrets in cluster)
secrets = get_secrets_provider()

# Get service credentials
creds = secrets.get_credentials(
    service="postgres",
    layer="layer1",
    environment="development"
)

database_url = creds["connection_string"]
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
from kstack_lib import get_environment_detector, get_cloud_storage_adapter

# Automatically uses local adapters
detector = get_environment_detector()
storage = get_cloud_storage_adapter(service="s3")

print(f"Environment: {detector.get_environment()}")  # "development"
# Storage automatically uses LocalStack at http://localhost:4566
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
from kstack_lib.types import KStackLayer, KStackEnvironment, KStackService

# Layers
layer = KStackLayer.LAYER_3_GLOBAL_INFRA

# Environments
env = KStackEnvironment.DEVELOPMENT

# Services
service = KStackService.S3
```

See [API Reference: Types](api/types.md) for complete documentation.

## Error Handling

KStack-lib uses custom exceptions for different error scenarios:

```python
from kstack_lib.any.exceptions import (
    KStackError,  # Base exception
    KStackConfigurationError,  # Config issues
    KStackServiceNotFoundError,  # Service not available
    KStackEnvironmentError,  # Wrong context
)

try:
    storage = get_cloud_storage_adapter(service="s3")
    storage.upload_file(bucket="my-bucket", key="file.json", body=data)
except KStackServiceNotFoundError:
    print("S3 service not configured")
except KStackConfigurationError as e:
    print(f"Configuration error: {e}")
```

## Next Steps

- Learn about the [IoC Container](architecture/ioc-container.md)
- Explore the [Cloud Abstraction Layer](architecture/cal-architecture.md)
- Read the [Architecture Overview](architecture/README.md)
