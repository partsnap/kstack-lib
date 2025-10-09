# Redis API Reference

Redis service discovery and configuration utilities.

## Overview

KStack provides automatic Redis discovery and configuration. The library can detect Redis instances across different layers and routes, providing connection details automatically.

## get_redis_config

Get Redis connection configuration for a specific volume.

::: kstack_lib.config.redis.get_redis_config
options:
show_root_heading: true
show_source: true

### Usage

```python
from kstack_lib.config import get_redis_config

# Get Redis configuration for a volume
config = get_redis_config("part-raw")

print(f"Host: {config['host']}")
print(f"Port: {config['port']}")
print(f"Volume: {config['volume']}")
```

### Parameters

- **volume** (str): The Redis volume name (e.g., "part-raw", "part-processed")
- **route** (str, optional): The route to use. Defaults to current active route.
- **layer** (KStackLayer, optional): The layer to search in. Defaults to Layer 3.

### Returns

Dictionary with keys:

- `host`: Redis hostname or IP address
- `port`: Redis port number (typically 6379)
- `volume`: The volume name

### Example: Connecting to Redis

```python
from kstack_lib.config import get_redis_config
import redis

# Get configuration
config = get_redis_config("part-raw")

# Create Redis client
client = redis.Redis(
    host=config['host'],
    port=config['port'],
    decode_responses=True
)

# Test connection
client.ping()
```

## Redis Volume Names

Common Redis volumes in KStack:

| Volume           | Purpose               |
| ---------------- | --------------------- |
| `part-raw`       | Raw part data storage |
| `part-processed` | Processed part data   |
| `audit`          | Audit log storage     |
| `cache`          | General caching       |

## Best Practices

### ✅ DO: Use get_redis_config for Discovery

```python
from kstack_lib.config import get_redis_config

config = get_redis_config("part-raw")
client = redis.Redis(host=config['host'], port=config['port'])
```

### ❌ DON'T: Hardcode Redis Endpoints

```python
# Avoid this - won't work across environments
client = redis.Redis(host='localhost', port=6379)
```

### ✅ DO: Handle Connection Errors

```python
from kstack_lib.config import get_redis_config
import redis

try:
    config = get_redis_config("part-raw")
    client = redis.Redis(host=config['host'], port=config['port'])
    client.ping()
except Exception as e:
    print(f"Redis connection failed: {e}")
```

## See Also

- [Configuration API](config.md) - Main configuration utilities
- [LocalStack API](localstack.md) - LocalStack service discovery
- [Redis Client Guide](../guide/redis-client.md) - User guide for Redis
