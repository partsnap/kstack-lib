# Redis Client

Comprehensive guide to using the Redis client factory.

## Overview

The Redis client factory provides automatic configuration discovery and async/sync context detection for connecting to PartSnap Redis instances.

## Basic Usage

### Synchronous Client

```python
from kstack_lib import create_redis_client

def get_part(mpn: str) -> dict | None:
    redis = create_redis_client(database='part-raw')
    data = redis.get(mpn)
    return json.loads(data) if data else None
```

### Asynchronous Client

```python
from kstack_lib import create_redis_client
import json

async def cache_part(mpn: str, data: dict) -> None:
    redis = create_redis_client(database='part-raw')
    try:
        await redis.setex(mpn, 3600, json.dumps(data))
    finally:
        await redis.aclose()
```

## Databases

Two Redis databases are available:

- `part-raw`: Main data cache
- `part-audit`: Audit logging (future)

```python
# Use part-raw (default)
redis = create_redis_client(database='part-raw')

# Use part-audit
redis_audit = create_redis_client(database='part-audit')
```

## Configuration Discovery

The client automatically discovers Redis configuration from:

1. **Local Development** - Vault file:

   ```yaml
   # ~/github/devops/partsnap-kstack/vault/dev/redis-cloud.yaml
   development:
     part-raw:
       host: redis-development-raw.layer-3-cloud
       port: 6379
       username: default
       password: partsnap-dev
   ```

2. **Kubernetes** - Secret:
   ```yaml
   apiVersion: v1
   kind: Secret
   metadata:
     name: redis-credentials-development
     namespace: layer-3-cloud
   data:
     redis-host: cmVkaXMtZGV2ZWxvcG1lbnQtcmF3LmxheWVyLTMtY2xvdWQ=
     redis-port: NjM3OQ==
     redis-username: ZGVmYXVsdA==
     redis-password: cGFydHNuYXAtZGV2
   ```

## Connection Parameters

All Redis clients are configured with:

- `decode_responses=True` - Automatically decode bytes to strings
- `socket_connect_timeout=5` - 5 second connection timeout
- `socket_timeout=5` - 5 second socket timeout

## Error Handling

```python
from redis import RedisError

async def safe_cache_get(mpn: str) -> dict | None:
    redis = create_redis_client(database='part-raw')
    try:
        data = await redis.get(mpn)
        return json.loads(data) if data else None
    except RedisError as e:
        logger.error(f"Redis error: {e}")
        return None
    finally:
        await redis.aclose()
```

## Best Practices

1. **Always close async clients**:

   ```python
   redis = create_redis_client()
   try:
       await redis.set('key', 'value')
   finally:
       await redis.aclose()
   ```

2. **Use TTL for cache entries**:

   ```python
   await redis.setex('key', 3600, 'value')  # 1 hour TTL
   ```

3. **Handle connection errors gracefully**:
   ```python
   try:
       data = await redis.get('key')
   except RedisError:
       # Fall back to database query
       data = await db.query(...)
   ```

## API Reference

See [API Documentation](../api/clients.md#redis-client) for complete reference.
