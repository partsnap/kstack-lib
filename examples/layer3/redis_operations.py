#!/usr/bin/env python3
"""
Example: Using partsnap_rediscache with external Redis access.

This example demonstrates how to connect to Redis instances in Layer 3
from the host machine using external NodePort access.

The setup provides:
- Multiple Redis instances (dev, test, data-collection, scratch)
- External access via NodePort (no need for kubectl port-forward)
- Auto-discovery of environment from .kstack.yaml
- Connection using partsnap_rediscache client

Requirements:
- Run from kstack-lib or partsnap-kstack directory (or subdirectory)
- .kstack.yaml must exist (auto-discovered in parent dirs)
- Layer 3 (Global Infrastructure) must be deployed
- Redis instance must be running (redis-dev for this example)

Usage:
    cd /home/lbrack/github/devops/kstack-lib
    python examples/layer3/redis_operations.py
"""

import asyncio

import yaml
from partsnap_rediscache import AsyncRedisCache
from partsnap_rediscache.config import RedisConfig

from kstack_lib.local.config.environment import LocalEnvironmentDetector


async def main() -> None:
    """Demonstrate Redis operations using partsnap_rediscache."""
    print("=" * 80)
    print("Redis Operations Example - External Access via NodePort")
    print("=" * 80)

    # Step 1: Auto-detect environment
    print("\n📋 Step 1: Auto-detect environment")
    try:
        env_detector = LocalEnvironmentDetector()
        environment = env_detector.get_environment()
        config_root = env_detector.get_config_root()

        print(f"   Environment: {environment} (from .kstack.yaml)")
        print(f"   Config root: {config_root}")
    except Exception as e:
        print(f"\n❌ Error: {e}")
        print("\n💡 Make sure you're running from kstack-lib or partsnap-kstack directory")
        print("   and .kstack.yaml exists with: environment: dev")
        return

    # Step 2: Load external access configuration
    print("\n📁 Step 2: Load external access configuration")
    env_config_file = config_root / "environments" / f"{environment}.yaml"

    if not env_config_file.exists():
        print(f"   ⚠️  Environment config not found: {env_config_file}")
        print("   Using default configuration")
        redis_host = "192.168.49.2"
        redis_port = 31379
    else:
        with open(env_config_file) as f:
            env_config = yaml.safe_load(f)

        redis_config = env_config.get("external_access", {}).get("redis", {}).get(environment, {})
        redis_host = redis_config.get("host", "192.168.49.2")
        redis_port = redis_config.get("port", 31379)

        print(f"   Loaded from: {env_config_file.name}")

    print("   Access method: NodePort (external)")
    print(f"   Host: {redis_host} (Minikube IP)")
    print(f"   Port: {redis_port} (redis-{environment}-external NodePort)")

    # Step 3: Configure Redis connection
    print("\n🔌 Step 3: Configure Redis connection")
    config = RedisConfig(
        host=redis_host,
        port=redis_port,
        username="default",
        password="partsnap-dev",  # Default dev password
        expiry_days=7,  # Default expiry for cached values
    )
    print("   ✓ Redis config created")

    # Step 4: Create Redis client
    print("\n🔗 Step 4: Create Redis client")
    redis_client = AsyncRedisCache(config)
    print("   ✓ AsyncRedisCache client created")

    try:
        # Step 5: Connect to Redis
        print("\n🤝 Step 5: Connect to Redis")
        await redis_client.connect()
        print(f"   ✓ Connected to redis-{environment}")

        # Step 6: Test basic operations - PING
        print("\n🏓 Step 6: Test PING")
        pong = await redis_client.ping()
        print(f"   ✓ PING response: {pong}")

        # Step 7: Check database size
        print("\n📊 Step 7: Check database size")
        dbsize = await redis_client.redis_client.dbsize()
        print(f"   ✓ Database contains {dbsize} keys")

        # Step 8: Set a value (using raw Redis commands)
        test_key = "example:simple-key"
        test_value = "Hello from Redis!"
        print("\n💾 Step 8: SET operation")
        print(f"   Key: {test_key}")
        print(f"   Value: {test_value}")
        await redis_client.redis_client.set(test_key, test_value)
        print("   ✓ Value set successfully")

        # Step 9: Get a value
        print("\n📥 Step 9: GET operation")
        retrieved = await redis_client.redis_client.get(test_key)
        print(f"   ✓ Retrieved value: {retrieved}")

        # Step 10: Check if key exists
        print("\n🔍 Step 10: Check key existence")
        exists = await redis_client.key_exists(test_key)
        print(f"   ✓ Key exists: {exists}")

        # Step 11: Store complex data as JSON string
        # Note: partsnap_rediscache uses RedisJSON module which requires redis-stack
        # For basic Redis, we'll manually serialize to JSON
        import json

        cache_key = "example:user:123"
        user_data = {
            "id": 123,
            "name": "Test User",
            "email": "test@example.com",
            "preferences": {"theme": "dark", "notifications": True},
        }
        print("\n💾 Step 11: Store complex data (JSON string)")
        print(f"   Key: {cache_key}")
        print(f"   Data: {user_data}")

        # Manually serialize to JSON string
        json_data = json.dumps(user_data)
        await redis_client.redis_client.set(cache_key, json_data)
        print("   ✓ Data stored successfully")

        # Step 12: Retrieve and deserialize
        print("\n📥 Step 12: Retrieve and deserialize")
        raw_data = await redis_client.redis_client.get(cache_key)
        cached_data = json.loads(raw_data)
        print(f"   ✓ Retrieved data: {cached_data}")

        # Step 13: Delete keys
        print("\n🗑️  Step 13: Cleanup")
        await redis_client.redis_client.delete(test_key)
        print(f"   ✓ Deleted {test_key}")

        await redis_client.redis_client.delete(cache_key)
        print(f"   ✓ Deleted {cache_key}")

        # Step 14: Final database size
        print("\n📊 Step 14: Final database size")
        final_dbsize = await redis_client.redis_client.dbsize()
        print(f"   ✓ Database contains {final_dbsize} keys")

    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback

        traceback.print_exc()
        return

    print("\n" + "=" * 80)
    print("✅ All Redis operations completed successfully!")
    print("=" * 80)

    # Additional information
    print("\n📝 Additional Information:")
    print("\n1. Internal Access (from within Kubernetes pods):")
    print("   - Use service DNS: redis-dev.layer-3-global-infra.svc.cluster.local:6379")
    print("\n2. External Access (from host machine):")
    print("   - Use NodePort: 192.168.49.2:31379")
    print("\n3. Other Redis instances:")
    print("   - redis-test: 192.168.49.2:31380 (scaled to 0 by default)")
    print("   - redis-data-collection: 192.168.49.2:31381")
    print("   - redis-scratch: 192.168.49.2:31382 (scaled to 0 by default)")
    print("\n4. To scale up stopped instances:")
    print("   kubectl scale statefulset redis-test -n layer-3-global-infra --replicas=1")


if __name__ == "__main__":
    asyncio.run(main())
