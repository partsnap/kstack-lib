"""
LocalStack client factory using configuration discovery.

This module provides helpers for creating AWS clients (boto3/aioboto3) that automatically
connect to LocalStack instances based on the active route. Automatically detects async
context and returns appropriate client type.

Example:
    # Synchronous usage (boto3)
    from kstack_lib.clients import create_localstack_client

    s3 = create_localstack_client('s3')
    s3.create_bucket(Bucket='my-bucket')
    s3.put_object(Bucket='my-bucket', Key='file.txt', Body=b'data')

    # Async usage (aioboto3) - detected automatically
    import asyncio

    async def main():
        s3 = create_localstack_client('s3')  # Returns async client
        async with s3 as client:
            await client.create_bucket(Bucket='my-bucket')
            await client.put_object(Bucket='my-bucket', Key='file.txt', Body=b'data')

    asyncio.run(main())

"""

import asyncio
import inspect
from typing import Any

from kstack_lib.config import get_localstack_config


def create_localstack_client(
    service_name: str,
    route: str | None = None,
) -> Any | Any:  # boto3.client or aioboto3.Session.client
    """
    Create an AWS client connected to LocalStack using automatic configuration discovery.

    Automatically detects whether the calling context is async and returns
    the appropriate client type (boto3 for sync, aioboto3 for async).

    Args:
        service_name: AWS service name (e.g., 's3', 'sqs', 'sns', 'rds', 'dynamodb')
        route: Optional route override (defaults to active route from KSTACK_ROUTE)

    Returns:
        boto3 client (sync) or aioboto3 client context manager (async)

    Raises:
        ImportError: If boto3/aioboto3 packages are not installed
        ValueError: If configuration cannot be found

    Example:
        # Sync usage - returns boto3 client
        s3 = create_localstack_client('s3')
        buckets = s3.list_buckets()

        # Async usage - returns aioboto3 client (detected automatically)
        async def my_func():
            s3_client = create_localstack_client('s3')
            async with s3_client as s3:
                response = await s3.list_buckets()

        # Works with all AWS services supported by LocalStack:
        # - s3, sqs, sns, lambda, dynamodb, rds, ec2, etc.

    """
    # Detect if we're in an async context
    is_async = _is_async_context()

    if is_async:
        return _create_async_localstack_client(service_name, route)
    else:
        return _create_sync_localstack_client(service_name, route)


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


def _create_sync_localstack_client(
    service_name: str,
    route: str | None = None,
) -> Any:
    """
    Create a synchronous boto3 client for LocalStack.

    Args:
        service_name: AWS service name
        route: Optional route override

    Returns:
        boto3 client instance

    """
    try:
        import boto3
    except ImportError as e:
        raise ImportError(
            "boto3 package is required. Install with: pip install boto3",
        ) from e

    # Get configuration from vault/secrets based on active route
    config = get_localstack_config(route=route)

    # Create boto3 client pointing to LocalStack
    return boto3.client(
        service_name,
        endpoint_url=config["endpoint_url"],
        aws_access_key_id=config.get("aws_access_key_id", "test"),
        aws_secret_access_key=config.get("aws_secret_access_key", "test"),
        region_name=config.get("region_name", "us-east-1"),
    )


def _create_async_localstack_client(
    service_name: str,
    route: str | None = None,
) -> Any:
    """
    Create an asynchronous aioboto3 client for LocalStack.

    Args:
        service_name: AWS service name
        route: Optional route override

    Returns:
        aioboto3 Session.client context manager

    """
    try:
        import aioboto3
    except ImportError as e:
        raise ImportError(
            "aioboto3 package is required. Install with: pip install aioboto3",
        ) from e

    # Get configuration from vault/secrets based on active route
    config = get_localstack_config(route=route)

    # Create aioboto3 session and return client context manager
    session = aioboto3.Session()
    return session.client(
        service_name,
        endpoint_url=config["endpoint_url"],
        aws_access_key_id=config.get("aws_access_key_id", "test"),
        aws_secret_access_key=config.get("aws_secret_access_key", "test"),
        region_name=config.get("region_name", "us-east-1"),
    )


def get_localstack_client(service_name: str, route: str | None = None) -> Any:
    """
    Alias for create_localstack_client() for backward compatibility.

    Args:
        service_name: AWS service name
        route: Optional route override

    Returns:
        boto3/aioboto3 client instance

    """
    return create_localstack_client(service_name, route)
