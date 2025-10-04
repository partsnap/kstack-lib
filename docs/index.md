# KStack Library

Infrastructure client library for PartSnap services.

## Overview

`kstack-lib` provides reusable components for Layer 2 services (like PartFinder) to connect to Layer 3 infrastructure (Redis, LocalStack) with automatic configuration discovery based on the active route.

**Key Features:**

- **Redis Client Factory**: Auto-discovers Redis instances based on active route
- **LocalStack Client Factory**: Auto-discovers LocalStack endpoints for AWS emulation
- **Route-based Configuration**: Supports development, testing, staging, scratch routes
- **Async/Sync Support**: Automatically detects async context and returns appropriate client
- **Vault & K8s Integration**: Reads configuration from vault files or Kubernetes secrets

## Quick Start

### Installation

```bash
# With pip
pip install git+https://github.com/partsnap/kstack-lib.git

# With uv
uv add git+https://github.com/partsnap/kstack-lib.git
```

### Redis Client Example

```python
from kstack_lib import create_redis_client

# Synchronous usage
redis = create_redis_client(database='part-raw')
redis.set('product:123', '{"name": "Widget"}')
value = redis.get('product:123')

# Async usage (automatically detected)
import asyncio

async def main():
    redis = create_redis_client(database='part-raw')  # Returns async client
    await redis.set('product:123', '{"name": "Widget"}')
    value = await redis.get('product:123')
    await redis.aclose()

asyncio.run(main())
```

### LocalStack Client Example

```python
from kstack_lib import create_localstack_client

# Get boto3 S3 client configured for LocalStack
s3 = create_localstack_client('s3')
s3.list_buckets()

# Async usage
import aioboto3

async def main():
    s3 = create_localstack_client('s3')  # Returns aioboto3 session
    async with s3 as client:
        response = await client.list_buckets()
        print(response['Buckets'])

asyncio.run(main())
```

## Architecture

### Layer Separation

- **Layer 3** (Infrastructure): Redis, LocalStack instances per route
- **Layer 2** (Services): PartFinder, other services using kstack-lib
- **kstack-lib**: Bridges Layer 2 ↔ Layer 3 with configuration discovery

Services depend on `kstack-lib`, NOT on `partsnap-kstack` (the deployment CLI).

### Route-Based Configuration

The library automatically discovers the active route from:

1. `KSTACK_ROUTE` environment variable (local development)
2. `kstack-route` ConfigMap in Kubernetes (deployed services)
3. Defaults to `development`

Then reads configuration from:

1. **Vault files** (local development):
   ```
   ~/github/devops/partsnap-kstack/vault/dev/redis-cloud.yaml
   ```

2. **Kubernetes Secrets** (deployed):
   ```yaml
   apiVersion: v1
   kind: Secret
   metadata:
     name: redis-credentials-development
     namespace: layer-3-cloud
   data:
     redis-host: <base64>
     redis-port: <base64>
     redis-username: <base64>
     redis-password: <base64>
   ```

## Next Steps

- [Getting Started Guide](getting-started.md)
- [Redis Client Documentation](guide/redis-client.md)
- [LocalStack Client Documentation](guide/localstack-client.md)
- [Configuration Discovery](guide/configuration.md)
- [API Reference](api/clients.md)

## License

Proprietary - PartSnap Inc.
