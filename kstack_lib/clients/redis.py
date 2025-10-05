"""
Redis client factory using configuration discovery.

This module provides helpers for creating Redis clients that automatically
discover the correct instance based on the active route and vault credentials.
Automatically detects async context and returns appropriate client type.

Example:
    # Synchronous usage
    from kstack_lib.clients import create_redis_client

    redis_raw = create_redis_client(database='part-raw')
    redis_raw.set('product:123', 'data')
    value = redis_raw.get('product:123')

    # Async usage (detected automatically)
    import asyncio

    async def main():
        redis = create_redis_client(database='part-raw')  # Returns async client
        await redis.set('product:123', 'data')
        value = await redis.get('product:123')
        await redis.aclose()

    asyncio.run(main())

"""

import asyncio
import inspect
from typing import TYPE_CHECKING, Literal

from kstack_lib.config import get_redis_config

if TYPE_CHECKING:
    from redis import Redis
    from redis.asyncio import Redis as AsyncRedis


def create_redis_client(
    database: Literal["part-raw", "part-audit"] = "part-raw",
) -> "Redis | AsyncRedis":  # type: ignore[name-defined]
    """
    Create a Redis client using automatic configuration discovery.

    Automatically detects whether the calling context is async and returns
    the appropriate client type (sync Redis or async Redis).

    Args:
        database: Which database to connect to ('part-raw' or 'part-audit')

    Returns:
        Redis or AsyncRedis client instance configured for the active route

    Raises:
        ImportError: If redis package is not installed
        ValueError: If configuration cannot be found

    Example:
        # Sync usage - returns sync client
        redis = create_redis_client(database='part-raw')
        redis.set('key', 'value')

        # Async usage - returns async client (detected automatically)
        async def my_func():
            redis = create_redis_client(database='part-raw')
            await redis.set('key', 'value')
            await redis.aclose()

        # Works in all environments (development, testing, staging, production)
        # Credentials come from vault or K8s Secrets automatically

    """
    # Detect if we're in an async context
    is_async = _is_async_context()

    if is_async:
        return _create_async_redis_client(database)
    else:
        return _create_sync_redis_client(database)


def _is_async_context() -> bool:
    """
    Detect if the calling code is in an async context.

    Returns:
        True if called from async function or coroutine, False otherwise

    """
    # Check if there's a running event loop
    try:
        asyncio.get_running_loop()
        return True
    except RuntimeError:
        pass

    # Check if caller is a coroutine function
    frame = inspect.currentframe()
    if frame and frame.f_back and frame.f_back.f_back:
        caller_frame = frame.f_back.f_back
        code = caller_frame.f_code
        # Check if the calling function is a coroutine
        if code.co_flags & inspect.CO_COROUTINE:
            return True

    return False


def _create_sync_redis_client(
    database: Literal["part-raw", "part-audit"] = "part-raw",
) -> "Redis":  # type: ignore[name-defined]
    """
    Create a synchronous Redis client.

    Args:
        database: Which database to connect to

    Returns:
        Synchronous Redis client instance

    """
    try:
        from redis import Redis
    except ImportError as e:
        raise ImportError(
            "redis package is required. Install with: pip install redis",
        ) from e

    # Get configuration from vault/secrets based on active route
    config = get_redis_config(database=database)

    # Create Redis client with discovered configuration
    return Redis(
        host=config["host"],
        port=config["port"],
        username=config["username"],
        password=config["password"],
        decode_responses=True,  # Automatically decode bytes to strings
        socket_connect_timeout=5,
        socket_timeout=5,
    )


def _create_async_redis_client(
    database: Literal["part-raw", "part-audit"] = "part-raw",
) -> "AsyncRedis":  # type: ignore[name-defined]
    """
    Create an asynchronous Redis client.

    Args:
        database: Which database to connect to

    Returns:
        Asynchronous Redis client instance

    """
    try:
        from redis.asyncio import Redis as AsyncRedis
    except ImportError as e:
        raise ImportError(
            "redis package with asyncio support is required. Install with: pip install redis",
        ) from e

    # Get configuration from vault/secrets based on active route
    config = get_redis_config(database=database)

    # Create async Redis client with discovered configuration
    return AsyncRedis(
        host=config["host"],
        port=config["port"],
        username=config["username"],
        password=config["password"],
        decode_responses=True,  # Automatically decode bytes to strings
        socket_connect_timeout=5,
        socket_timeout=5,
    )


def get_redis_client(
    database: Literal["part-raw", "part-audit"] = "part-raw",
) -> "Redis | AsyncRedis":  # type: ignore[name-defined]
    """
    Alias for create_redis_client() for backward compatibility.

    Args:
        database: Which database to connect to ('part-raw' or 'part-audit')

    Returns:
        Redis client instance configured for the active route

    """
    return create_redis_client(database=database)
