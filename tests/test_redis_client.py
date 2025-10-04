"""Unit tests for Redis client factory."""

import asyncio
from unittest.mock import MagicMock, patch

import pytest

from kstack_lib.clients.redis import (
    _create_async_redis_client,
    _create_sync_redis_client,
    _is_async_context,
    create_redis_client,
    get_redis_client,
)


@pytest.mark.unit
def test_is_async_context_returns_false_in_sync_context():
    """Test that _is_async_context returns False when called from sync function."""
    assert _is_async_context() is False


@pytest.mark.unit
@pytest.mark.asyncio
async def test_is_async_context_returns_true_in_async_context():
    """Test that _is_async_context returns True when called from async function."""
    # In an async function with running event loop, should return True
    assert _is_async_context() is True


@pytest.mark.unit
@patch("kstack_lib.clients.redis.get_redis_config")
@patch("redis.Redis")
def test_create_sync_redis_client_part_raw(mock_redis, mock_get_config):
    """Test creating synchronous Redis client for part-raw database."""
    mock_config = {
        "host": "localhost",
        "port": 6379,
        "username": "default",
        "password": "test-password",
    }
    mock_get_config.return_value = mock_config
    mock_client = MagicMock()
    mock_redis.return_value = mock_client

    client = _create_sync_redis_client(database="part-raw")

    # Verify config was requested for correct database
    mock_get_config.assert_called_once_with(database="part-raw")

    # Verify Redis client was created with correct parameters
    mock_redis.assert_called_once_with(
        host="localhost",
        port=6379,
        username="default",
        password="test-password",
        decode_responses=True,
        socket_connect_timeout=5,
        socket_timeout=5,
    )
    assert client == mock_client


@pytest.mark.unit
@patch("kstack_lib.clients.redis.get_redis_config")
@patch("redis.Redis")
def test_create_sync_redis_client_part_audit(mock_redis, mock_get_config):
    """Test creating synchronous Redis client for part-audit database."""
    mock_config = {
        "host": "redis-audit",
        "port": 6380,
        "username": "audit",
        "password": "audit-password",
    }
    mock_get_config.return_value = mock_config
    mock_client = MagicMock()
    mock_redis.return_value = mock_client

    client = _create_sync_redis_client(database="part-audit")

    # Verify config was requested for part-audit
    mock_get_config.assert_called_once_with(database="part-audit")
    assert client == mock_client


@pytest.mark.unit
def test_create_sync_redis_client_import_error():
    """Test that ImportError is raised if redis package is not installed."""
    with patch("builtins.__import__", side_effect=ImportError("No module named 'redis'")):
        with pytest.raises(ImportError, match="redis package is required"):
            _create_sync_redis_client()


@pytest.mark.unit
@patch("kstack_lib.clients.redis.get_redis_config")
@patch("redis.asyncio.Redis")
def test_create_async_redis_client_part_raw(mock_async_redis, mock_get_config):
    """Test creating asynchronous Redis client for part-raw database."""
    mock_config = {
        "host": "localhost",
        "port": 6379,
        "username": "default",
        "password": "test-password",
    }
    mock_get_config.return_value = mock_config
    mock_client = MagicMock()
    mock_async_redis.return_value = mock_client

    client = _create_async_redis_client(database="part-raw")

    # Verify config was requested for correct database
    mock_get_config.assert_called_once_with(database="part-raw")

    # Verify async Redis client was created with correct parameters
    mock_async_redis.assert_called_once_with(
        host="localhost",
        port=6379,
        username="default",
        password="test-password",
        decode_responses=True,
        socket_connect_timeout=5,
        socket_timeout=5,
    )
    assert client == mock_client


@pytest.mark.unit
@patch("kstack_lib.clients.redis.get_redis_config")
@patch("redis.asyncio.Redis")
def test_create_async_redis_client_part_audit(mock_async_redis, mock_get_config):
    """Test creating asynchronous Redis client for part-audit database."""
    mock_config = {
        "host": "redis-audit",
        "port": 6380,
        "username": "audit",
        "password": "audit-password",
    }
    mock_get_config.return_value = mock_config
    mock_client = MagicMock()
    mock_async_redis.return_value = mock_client

    client = _create_async_redis_client(database="part-audit")

    # Verify config was requested for part-audit
    mock_get_config.assert_called_once_with(database="part-audit")
    assert client == mock_client


@pytest.mark.unit
def test_create_async_redis_client_import_error():
    """Test that ImportError is raised if redis asyncio is not available."""
    with patch("builtins.__import__", side_effect=ImportError("No module named 'redis.asyncio'")):
        with pytest.raises(ImportError, match="redis package with asyncio support is required"):
            _create_async_redis_client()


@pytest.mark.unit
@patch("kstack_lib.clients.redis._is_async_context")
@patch("kstack_lib.clients.redis._create_sync_redis_client")
def test_create_redis_client_sync_context(mock_sync_client, mock_is_async):
    """Test that create_redis_client returns sync client in sync context."""
    mock_is_async.return_value = False
    mock_client = MagicMock()
    mock_sync_client.return_value = mock_client

    client = create_redis_client(database="part-raw")

    mock_sync_client.assert_called_once_with("part-raw")
    assert client == mock_client


@pytest.mark.unit
@patch("kstack_lib.clients.redis._is_async_context")
@patch("kstack_lib.clients.redis._create_async_redis_client")
def test_create_redis_client_async_context(mock_async_client, mock_is_async):
    """Test that create_redis_client returns async client in async context."""
    mock_is_async.return_value = True
    mock_client = MagicMock()
    mock_async_client.return_value = mock_client

    client = create_redis_client(database="part-audit")

    mock_async_client.assert_called_once_with("part-audit")
    assert client == mock_client


@pytest.mark.unit
@patch("kstack_lib.clients.redis.create_redis_client")
def test_get_redis_client_is_alias(mock_create_client):
    """Test that get_redis_client is an alias for create_redis_client."""
    mock_client = MagicMock()
    mock_create_client.return_value = mock_client

    client = get_redis_client(database="part-raw")

    mock_create_client.assert_called_once_with(database="part-raw")
    assert client == mock_client


@pytest.mark.unit
@patch("kstack_lib.clients.redis._is_async_context")
@patch("kstack_lib.clients.redis._create_sync_redis_client")
def test_create_redis_client_default_database(mock_sync_client, mock_is_async):
    """Test that create_redis_client defaults to part-raw database."""
    mock_is_async.return_value = False
    mock_client = MagicMock()
    mock_sync_client.return_value = mock_client

    client = create_redis_client()  # No database specified

    # Should default to part-raw
    mock_sync_client.assert_called_once_with("part-raw")
    assert client == mock_client


@pytest.mark.unit
@patch("kstack_lib.clients.redis.get_redis_config")
@patch("redis.Redis")
def test_sync_client_configuration_parameters(mock_redis, mock_get_config):
    """Test that sync client is created with correct timeout and decode settings."""
    mock_config = {
        "host": "redis.local",
        "port": 6379,
        "username": "user",
        "password": "pass",
    }
    mock_get_config.return_value = mock_config

    _create_sync_redis_client()

    # Verify decode_responses and timeout settings
    call_kwargs = mock_redis.call_args[1]
    assert call_kwargs["decode_responses"] is True
    assert call_kwargs["socket_connect_timeout"] == 5
    assert call_kwargs["socket_timeout"] == 5


@pytest.mark.unit
@patch("kstack_lib.clients.redis.get_redis_config")
@patch("redis.asyncio.Redis")
def test_async_client_configuration_parameters(mock_async_redis, mock_get_config):
    """Test that async client is created with correct timeout and decode settings."""
    mock_config = {
        "host": "redis.local",
        "port": 6379,
        "username": "user",
        "password": "pass",
    }
    mock_get_config.return_value = mock_config

    _create_async_redis_client()

    # Verify decode_responses and timeout settings
    call_kwargs = mock_async_redis.call_args[1]
    assert call_kwargs["decode_responses"] is True
    assert call_kwargs["socket_connect_timeout"] == 5
    assert call_kwargs["socket_timeout"] == 5
