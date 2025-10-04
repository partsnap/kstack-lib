# Getting Started

This guide will help you get started with `kstack-lib` in your PartSnap service.

## Installation

### Using uv (Recommended)

```toml
# pyproject.toml
[project]
dependencies = [
    "kstack-lib @ git+https://github.com/partsnap/kstack-lib.git",
]
```

Then run:
```bash
uv sync
```

### Using pip

```bash
pip install git+https://github.com/partsnap/kstack-lib.git
```

## Basic Usage

### Redis Client

```python
from kstack_lib import create_redis_client

# In a sync function
def get_cached_part(mpn: str):
    redis = create_redis_client(database='part-raw')
    return redis.get(mpn)

# In an async function
async def cache_part(mpn: str, data: dict):
    redis = create_redis_client(database='part-raw')
    try:
        await redis.setex(mpn, 3600, json.dumps(data))
    finally:
        await redis.aclose()
```

### LocalStack Client

```python
from kstack_lib import create_localstack_client

# S3 client
s3 = create_localstack_client('s3')
buckets = s3.list_buckets()

# DynamoDB client (future)
dynamodb = create_localstack_client('dynamodb')
```

## Configuration

### Local Development

Set the route environment variable:

```bash
export KSTACK_ROUTE=development
```

Create vault configuration file:

```bash
mkdir -p ~/github/devops/partsnap-kstack/vault/dev
```

```yaml
# ~/github/devops/partsnap-kstack/vault/dev/redis-cloud.yaml
development:
  part-raw:
    host: redis-development-raw.layer-3-cloud
    port: 6379
    username: default
    password: partsnap-dev
```

### Kubernetes Deployment

The library automatically reads from Kubernetes secrets:

```yaml
apiVersion: v1
kind: Secret
metadata:
  name: redis-credentials-development
  namespace: layer-3-cloud
type: Opaque
data:
  redis-host: <base64-encoded>
  redis-port: <base64-encoded>
  redis-username: <base64-encoded>
  redis-password: <base64-encoded>
```

Mount the `kstack-route` ConfigMap:

```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: my-service
spec:
  template:
    spec:
      containers:
      - name: my-service
        envFrom:
        - configMapRef:
            name: kstack-route
            namespace: layer-3-cloud
```

## Next Steps

- [Redis Client Guide](guide/redis-client.md)
- [LocalStack Client Guide](guide/localstack-client.md)
- [Configuration Discovery](guide/configuration.md)
- [API Reference](api/clients.md)
