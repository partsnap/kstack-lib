# Redis Examples - External Access

This guide shows how to connect to Redis instances in Layer 3 from your host machine using external NodePort access.

## Overview

Layer 3 provides multiple Redis instances for different purposes:

| Instance                | Purpose               | Default State | External Port |
| ----------------------- | --------------------- | ------------- | ------------- |
| `redis-dev`             | Development data      | Running       | 31379         |
| `redis-test`            | Test data             | Stopped       | 31380         |
| `redis-data-collection` | Raw API responses     | Running       | 31381         |
| `redis-scratch`         | Temporary experiments | Stopped       | 31382         |

## Architecture

```
┌──────────────────────────────────────────────────────────────┐
│                    Host Machine (Developer)                   │
│                                                               │
│  ┌─────────────────────────────────────────────────────────┐ │
│  │  Application using partsnap_rediscache                  │ │
│  │                                                          │ │
│  │  AsyncRedisCache(                                       │ │
│  │    host="192.168.49.2",    ← Minikube IP               │ │
│  │    port=31379               ← NodePort                  │ │
│  │  )                                                       │ │
│  └──────────────────────┬──────────────────────────────────┘ │
└─────────────────────────┼────────────────────────────────────┘
                          │
                          │ TCP: 192.168.49.2:31379
                          ▼
┌──────────────────────────────────────────────────────────────┐
│                  Kubernetes Cluster (Minikube)                │
│                                                               │
│  Layer 3: layer-3-global-infra namespace                     │
│                                                               │
│  ┌─────────────────────────────────────────────────────────┐│
│  │  Service: redis-dev-external (NodePort)                 ││
│  │  - Type: NodePort                                       ││
│  │  - Port: 6379                                           ││
│  │  - NodePort: 31379                                      ││
│  │  - Selector: app=redis, volume-type=dev                ││
│  └──────────────────────┬──────────────────────────────────┘│
│                         │                                     │
│                         ▼                                     │
│  ┌─────────────────────────────────────────────────────────┐│
│  │  StatefulSet: redis-dev                                 ││
│  │  - Replicas: 1                                          ││
│  │  - Volume: redis-dev-pvc (10GB)                         ││
│  │                                                          ││
│  │  Pod: redis-dev-0                                       ││
│  │    - Image: redis:7.2-alpine                            ││
│  │    - Port: 6379                                         ││
│  └─────────────────────────────────────────────────────────┘│
└──────────────────────────────────────────────────────────────┘
```

## External vs Internal Access

### External Access (Host Machine → Kubernetes)

Use **NodePort** for development from your host machine:

```python
from partsnap_rediscache import AsyncRedisCache
from partsnap_rediscache.config import RedisConfig

config = RedisConfig(
    host="192.168.49.2",  # Minikube IP
    port=31379,            # NodePort
    username="default",
    password="partsnap-dev"
)

redis_client = AsyncRedisCache(config)
```

**Advantages:**

- No `kubectl port-forward` needed
- Connection persists even if kubectl restarts
- Multiple applications can connect simultaneously

### Internal Access (Pod → Pod)

Use **Service DNS** for applications running inside Kubernetes:

```python
config = RedisConfig(
    host="redis-dev.layer-3-global-infra.svc.cluster.local",
    port=6379,  # Standard Redis port
    username="default",
    password="partsnap-dev"
)
```

**Advantages:**

- Lower latency (no external network hop)
- Doesn't consume NodePort
- Standard Kubernetes service discovery

## Basic Example: Redis Operations

See [`examples/layer3/redis_operations.py`](../../examples/layer3/redis_operations.py) for a complete working example.

### Step-by-Step Walkthrough

#### 1. Configure Connection

```python
from partsnap_rediscache.config import RedisConfig

config = RedisConfig(
    host="192.168.49.2",      # Minikube IP
    port=31379,                # NodePort for redis-dev
    username="default",
    password="partsnap-dev",   # Default dev password
    expiry_days=7              # Default TTL for cached values
)
```

**Configuration options:**

- `host`: Redis server hostname or IP
- `port`: Redis server port
- `username`: Redis ACL username (usually "default")
- `password`: Redis password
- `expiry_days`: Default expiration time for cached values
- `db`: Redis database number (default: 0)

#### 2. Create Client

```python
from partsnap_rediscache import AsyncRedisCache

redis_client = AsyncRedisCache(config)
```

The `AsyncRedisCache` provides:

- Async/await interface
- Automatic JSON serialization/deserialization
- TTL management for cached values
- Key existence checking

#### 3. Connect

```python
await redis_client.connect()
```

This establishes the connection and verifies Redis is accessible.

#### 4. Basic Operations - SET/GET

```python
# Set a simple value
await redis_client.redis_client.set("my-key", "my-value")

# Get a value
value = await redis_client.redis_client.get("my-key")
print(value)  # "my-value"

# Check if key exists
exists = await redis_client.key_exists("my-key")
print(exists)  # True

# Delete a key
await redis_client.redis_client.delete("my-key")
```

**Note:** `.redis_client` gives you direct access to the underlying `redis.asyncio.Redis` client for low-level operations.

#### 5. Cache Complex Data (JSON)

`partsnap_rediscache` automatically serializes Python objects to JSON:

```python
user_data = {
    "id": 123,
    "name": "John Doe",
    "email": "john@example.com",
    "preferences": {
        "theme": "dark",
        "notifications": True
    }
}

# Store with automatic JSON serialization
await redis_client.set_cache("user:123", user_data)

# Retrieve with automatic JSON deserialization
retrieved = await redis_client.get_cache("user:123")
print(retrieved)  # {'id': 123, 'name': 'John Doe', ...}
```

**Behind the scenes:**

1. `set_cache()` converts dict → JSON → stores in Redis
2. Sets TTL based on `expiry_days` config
3. `get_cache()` retrieves → parses JSON → returns dict

#### 6. PING Test

```python
pong = await redis_client.ping()
print(pong)  # True
```

Verifies the connection is alive.

#### 7. Database Size

```python
count = await redis_client.redis_client.dbsize()
print(f"Database contains {count} keys")
```

Returns the total number of keys in the current database.

## Multiple Redis Instances

### Connecting to Different Instances

```python
# Development data
redis_dev = AsyncRedisCache(RedisConfig(
    host="192.168.49.2",
    port=31379,
    password="partsnap-dev"
))

# Test data (must be scaled up first)
redis_test = AsyncRedisCache(RedisConfig(
    host="192.168.49.2",
    port=31380,
    password="partsnap-test"
))

# Data collection (raw API responses)
redis_data_collection = AsyncRedisCache(RedisConfig(
    host="192.168.49.2",
    port=31381,
    password="partsnap-dev"
))
```

### Scaling Instances Up/Down

Some instances are scaled to 0 by default to save resources:

```bash
# Scale up redis-test
kubectl scale statefulset redis-test \
  -n layer-3-global-infra --replicas=1

# Wait for pod to be ready
kubectl wait --for=condition=ready pod/redis-test-0 \
  -n layer-3-global-infra --timeout=60s

# Scale back down
kubectl scale statefulset redis-test \
  -n layer-3-global-infra --replicas=0
```

## Advanced Features

### TTL and Expiration

Control how long cached values persist:

```python
# Use default TTL from config (7 days)
await redis_client.set_cache("key1", {"data": "value"})

# Or set custom expiration
await redis_client.redis_client.setex(
    "key2",
    86400,  # 24 hours in seconds
    '{"data": "value"}'
)
```

### Pattern Matching

Find keys matching a pattern:

```python
# Get all user keys
keys = await redis_client.redis_client.keys("user:*")

for key in keys:
    data = await redis_client.get_cache(key)
    print(f"{key}: {data}")
```

**Warning:** `KEYS` scans the entire database. Use `SCAN` for production:

```python
async for key in redis_client.redis_client.scan_iter(match="user:*"):
    print(key)
```

### Batch Operations

```python
# Set multiple keys at once
pipeline = redis_client.redis_client.pipeline()
pipeline.set("key1", "value1")
pipeline.set("key2", "value2")
pipeline.set("key3", "value3")
await pipeline.execute()

# Get multiple keys
values = await redis_client.redis_client.mget(["key1", "key2", "key3"])
```

### Hash Operations

Redis hashes are great for storing objects:

```python
# Store user as hash
await redis_client.redis_client.hset(
    "user:123",
    mapping={
        "name": "John Doe",
        "email": "john@example.com",
        "age": "30"
    }
)

# Get single field
name = await redis_client.redis_client.hget("user:123", "name")

# Get all fields
user = await redis_client.redis_client.hgetall("user:123")
```

## Configuration Files

### Environment Configuration

`environments/dev.yaml` documents the external access endpoints:

```yaml
external_access:
  redis:
    dev:
      host: "192.168.49.2"
      port: 31379
      access_method: "nodeport"
      internal_service: "redis-dev.layer-3-global-infra.svc.cluster.local:6379"
```

### NodePort Services

Each Redis instance has an external NodePort service:

```yaml
# kstack/manifests/layer-3/redis/redis-dev-external.yaml
apiVersion: v1
kind: Service
metadata:
  name: redis-dev-external
  namespace: layer-3-global-infra
spec:
  type: NodePort
  selector:
    app: redis
    volume-type: dev
  ports:
    - port: 6379
      targetPort: 6379
      nodePort: 31379
```

## Testing

Run the example from the partsnap-kstack directory:

```bash
cd /home/lbrack/github/devops/partsnap-kstack
.venv/bin/python ../kstack-lib/examples/layer3/redis_operations.py
```

The example will:

1. Auto-discover the environment from `.kstack.yaml` in the current directory
2. Auto-discover config_root (partsnap-kstack root directory)
3. Load external access configuration from `environments/dev.yaml`
4. Connect to Redis via NodePort at `192.168.49.2:31379`

Expected output:

```
================================================================================
Redis Operations Example - External Access via NodePort
================================================================================

📋 Step 1: Configure Redis connection
   Environment: dev
   Access method: NodePort (external)
   Host: 192.168.49.2 (Minikube IP)
   Port: 31379 (redis-dev-external NodePort)

🔌 Step 2: Create Redis client
   ✓ AsyncRedisCache client created

🤝 Step 3: Connect to Redis
   ✓ Connected to redis-dev

🏓 Step 4: Test PING
   ✓ PING response: True

📊 Step 5: Check database size
   ✓ Database contains 0 keys

💾 Step 6: SET operation
   Key: example:simple-key
   Value: Hello from Redis!
   ✓ Value set successfully

📥 Step 7: GET operation
   ✓ Retrieved value: Hello from Redis!

🔍 Step 8: Check key existence
   ✓ Key exists: True

💾 Step 9: Cache complex data (JSON)
   Key: example:user:123
   Data: {'id': 123, 'name': 'Test User', ...}
   ✓ Data cached successfully

📥 Step 10: Retrieve cached data
   ✓ Retrieved data: {'id': 123, 'name': 'Test User', ...}

🗑️  Step 11: Cleanup
   ✓ Deleted example:simple-key
   ✓ Deleted example:user:123

📊 Step 12: Final database size
   ✓ Database contains 0 keys

================================================================================
✅ All Redis operations completed successfully!
================================================================================
```

## Troubleshooting

### Connection refused to 192.168.49.2:31379

**Problem:** Can't connect to Redis

**Solutions:**

1. Check Minikube IP: `minikube ip` (should be 192.168.49.2)
2. Verify Redis is running:
   ```bash
   kubectl get pods -n layer-3-global-infra | grep redis-dev
   ```
3. Check NodePort service:
   ```bash
   kubectl get svc redis-dev-external -n layer-3-global-infra
   ```
4. Test with redis-cli:
   ```bash
   redis-cli -h 192.168.49.2 -p 31379 ping
   ```

### Authentication failed

**Problem:** Password incorrect

**Solution:** Get password from secret:

```bash
kubectl get secret redis-credentials-dev \
  -n layer-3-global-infra \
  -o jsonpath='{.data.redis-password}' | base64 -d
```

### Pod not running

**Problem:** Redis pod is scaled to 0

**Solution:** Scale it up:

```bash
kubectl scale statefulset redis-dev \
  -n layer-3-global-infra --replicas=1
```

## Performance Considerations

### Connection Pooling

`AsyncRedisCache` uses connection pooling automatically. Reuse the client instance:

```python
# ✅ Good - one client, many operations
redis_client = AsyncRedisCache(config)
await redis_client.connect()

for i in range(1000):
    await redis_client.set_cache(f"key:{i}", {"value": i})

# ❌ Bad - creates new connection each time
for i in range(1000):
    client = AsyncRedisCache(config)
    await client.connect()
    await client.set_cache(f"key:{i}", {"value": i})
```

### Pipeline Operations

Use pipelines for bulk operations:

```python
pipeline = redis_client.redis_client.pipeline()
for i in range(1000):
    pipeline.set(f"key:{i}", f"value:{i}")
await pipeline.execute()  # Single network round trip
```

### External vs Internal Latency

- **External (NodePort)**: ~1-2ms latency
- **Internal (Service DNS)**: ~0.1-0.2ms latency

For latency-sensitive applications running in Kubernetes, use internal service DNS.

## See Also

- [CAL Examples](./cal_examples.md)
- [ConfigMap Guide](../guides/configmaps.md)
- [Layer 3 Architecture](../architecture/layers-implementation.md)
- [partsnap_rediscache Documentation](https://github.com/partsnap/partsnap-rediscache)
