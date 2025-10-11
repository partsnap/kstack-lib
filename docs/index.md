# KStack Library

**Infrastructure client library for PartSnap Kubernetes stack**

KStack-lib provides a unified, context-aware interface for accessing infrastructure services across development and production environments.

## Key Features

- **Context-Aware Architecture**: Automatically adapts behavior based on runtime environment (local development vs. Kubernetes cluster)
- **Cloud Abstraction Layer (CAL)**: Unified interface for cloud storage (S3/LocalStack) with pluggable adapters
- **Dependency Injection**: IoC container manages dependencies and wiring across contexts
- **Type Safety**: Comprehensive type system for layers, environments, and services
- **Zero Configuration**: Works out-of-the-box in both local and cluster contexts

## Quick Start

### Installation

```bash
uv add kstack-lib
```

### Basic Usage

```python
from pathlib import Path
from kstack_lib.any.container import get_environment_detector
from kstack_lib.cal import CloudContainer
from kstack_lib.config import ConfigMap
from kstack_lib.types import KStackLayer, KStackEnvironment

# Automatically detects environment (dev/staging/production)
detector = get_environment_detector()
environment = detector.get_environment()

# Create configuration and cloud container
cfg = ConfigMap(
    layer=KStackLayer.LAYER_3_GLOBAL_INFRA,
    environment=KStackEnvironment.DEVELOPMENT,
)

# Get cloud storage (S3 in cluster, LocalStack locally)
with CloudContainer(cfg, config_root=Path("./config"), vault_root=Path("./vault")) as cloud:
    storage = cloud.object_storage()

    # Upload a file
    with open("data.json", "rb") as f:
        storage.upload_object(
            bucket="my-bucket",
            key="data/file.json",
            file_obj=f,
            content_type="application/json"
        )
```

## Architecture Overview

KStack-lib uses a three-tier architecture:

1. **`kstack_lib.any`**: Shared code that works everywhere (protocols, types, container)
2. **`kstack_lib.local`**: Local development adapters (uses vault files, local configs)
3. **`kstack_lib.cluster`**: Production adapters (uses K8s ConfigMaps and Secrets)

The IoC container automatically selects the correct implementation based on runtime context.

## Documentation Structure

- **[Getting Started](getting-started.md)**: Quick start guide and common use cases
- **[Architecture](architecture/README.md)**: Deep dive into design patterns and structure
- **[API Reference](api/types.md)**: Type system and API documentation
- **[Development](development/testing.md)**: Testing and contributing guide

## Related Projects

- **[partmaster](https://github.com/partsnap/partmaster)**: API service using kstack-lib
- **[kstack CLI](https://github.com/partsnap/kstack-cli)**: Deployment and management tools

## License

Proprietary - PartSnap LLC © 2025
