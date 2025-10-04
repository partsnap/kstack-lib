# KStack Library

Infrastructure client library for PartSnap services.

## Overview

`kstack-lib` provides reusable components for Layer 2 services (like PartFinder) to connect to Layer 3 infrastructure (Redis, LocalStack) with automatic configuration discovery based on the active route.

This library is intentionally separate from `partsnap-kstack` (the CLI deployment tool) to avoid coupling library code with deployment tools.

## Features

- **Redis Client Factory**: Auto-discovers Redis instances based on active route
- **LocalStack Client Factory**: Auto-discovers LocalStack endpoints for AWS emulation
- **Route-based Configuration**: Supports development, testing, staging, scratch routes
- **Async/Sync Support**: Automatically detects async context and returns appropriate client
- **Vault & K8s Integration**: Reads configuration from vault files or Kubernetes secrets

## Installation

```bash
pip install git+https://github.com/partsnap/kstack-lib.git
```

Or with uv:

```bash
uv add git+https://github.com/partsnap/kstack-lib.git
```

## Usage

### Redis Client

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

### Configuration Discovery

```python
from kstack_lib import get_redis_config

# Get configuration for active route
config = get_redis_config(database='part-raw')
# Returns: {"host": "...", "port": 6379, "username": "...", "password": "..."}
```

### Route Management

The library automatically discovers the active route from:
1. `KSTACK_ROUTE` environment variable (local development)
2. `kstack-route` ConfigMap in Kubernetes (deployed services)
3. Defaults to `development`

## Architecture

### Layer Separation

- **Layer 3** (Infrastructure): Redis, LocalStack instances per route
- **Layer 2** (Services): PartFinder, other services using kstack-lib
- **kstack-lib**: Bridges Layer 2 ↔ Layer 3 with configuration discovery

Services depend on `kstack-lib`, NOT on `partsnap-kstack` (the deployment CLI).

## Development

```bash
# Clone repository
git clone https://github.com/partsnap/kstack-lib.git
cd kstack-lib

# Install dependencies
uv sync

# Run tests
uv run pytest

# Build documentation
uv run mkdocs serve
```

## Documentation

Full documentation available at [kstack-lib.readthedocs.io](https://kstack-lib.readthedocs.io/)

## License

Proprietary - PartSnap Inc.
