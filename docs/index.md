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
from kstack_lib import get_environment_detector, get_cloud_storage_adapter

# Automatically detects environment (dev/staging/production)
detector = get_environment_detector()
environment = detector.get_environment()

# Get cloud storage adapter (S3 in cluster, LocalStack locally)
storage = get_cloud_storage_adapter(service="s3")

# Upload a file
with open("data.json", "rb") as f:
    storage.upload_file(
        bucket="my-bucket",
        key="data/file.json",
        body=f
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
