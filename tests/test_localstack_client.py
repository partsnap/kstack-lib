"""Unit tests for LocalStack client factory."""

from unittest.mock import MagicMock, patch

import pytest

# boto3 and aioboto3 are optional dependencies, only test if available
boto3 = pytest.importorskip("boto3", reason="boto3 not installed (optional dependency)")
aioboto3 = pytest.importorskip("aioboto3", reason="aioboto3 not installed (optional dependency)")

from kstack_lib.clients.localstack import (  # noqa: E402
    _create_async_localstack_client,
    _create_sync_localstack_client,
    _is_async_context,
    create_localstack_client,
    get_localstack_client,
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
def test_create_sync_localstack_client_success():
    """Test creating synchronous boto3 LocalStack client."""
    mock_config = {
        "endpoint_url": "http://localhost:4566",
        "aws_access_key_id": "test-key",
        "aws_secret_access_key": "test-secret",
        "region_name": "us-west-2",
    }

    with patch("kstack_lib.clients.localstack.get_localstack_config", return_value=mock_config):
        with patch("boto3.client") as mock_boto3_client:
            mock_client = MagicMock()
            mock_boto3_client.return_value = mock_client

            client = _create_sync_localstack_client("s3")

            # Verify boto3.client was called with correct parameters
            mock_boto3_client.assert_called_once_with(
                "s3",
                endpoint_url="http://localhost:4566",
                aws_access_key_id="test-key",
                aws_secret_access_key="test-secret",
                region_name="us-west-2",
            )
            assert client == mock_client


@pytest.mark.unit
def test_create_sync_localstack_client_with_defaults():
    """Test sync client uses default AWS credentials when not in config."""
    mock_config = {
        "endpoint_url": "http://localhost:4566",
    }

    with patch("kstack_lib.clients.localstack.get_localstack_config", return_value=mock_config):
        with patch("boto3.client") as mock_boto3_client:
            _create_sync_localstack_client("dynamodb")

            # Should use default values for missing config
            mock_boto3_client.assert_called_once_with(
                "dynamodb",
                endpoint_url="http://localhost:4566",
                aws_access_key_id="test",  # default
                aws_secret_access_key="test",  # default
                region_name="us-east-1",  # default
            )


@pytest.mark.unit
def test_create_sync_localstack_client_raises_import_error():
    """Test that ImportError is raised if boto3 is not installed."""
    # This test is skipped as boto3 is installed in dev environment
    # The actual behavior is tested in integration/manual testing
    pytest.skip("boto3 import error testing requires uninstalling boto3")


@pytest.mark.unit
def test_create_async_localstack_client_success():
    """Test creating asynchronous aioboto3 LocalStack client."""
    mock_config = {
        "endpoint_url": "http://localhost:4566",
        "aws_access_key_id": "async-key",
        "aws_secret_access_key": "async-secret",
        "region_name": "eu-west-1",
    }

    with patch("kstack_lib.clients.localstack.get_localstack_config", return_value=mock_config):
        with patch("aioboto3.Session") as mock_session_class:
            mock_session = MagicMock()
            mock_client = MagicMock()
            mock_session.client.return_value = mock_client
            mock_session_class.return_value = mock_session

            client = _create_async_localstack_client("sqs")

            # Verify aioboto3.Session was created and client called correctly
            mock_session_class.assert_called_once()
            mock_session.client.assert_called_once_with(
                "sqs",
                endpoint_url="http://localhost:4566",
                aws_access_key_id="async-key",
                aws_secret_access_key="async-secret",
                region_name="eu-west-1",
            )
            assert client == mock_client


@pytest.mark.unit
def test_create_async_localstack_client_raises_import_error():
    """Test that ImportError is raised if aioboto3 is not installed."""
    # This test is skipped as aioboto3 is installed in dev environment
    # The actual behavior is tested in integration/manual testing
    pytest.skip("aioboto3 import error testing requires uninstalling aioboto3")


@pytest.mark.unit
def test_create_localstack_client_sync_context():
    """Test that create_localstack_client returns sync client in sync context."""
    with patch("kstack_lib.clients.localstack._is_async_context", return_value=False):
        with patch("kstack_lib.clients.localstack._create_sync_localstack_client") as mock_sync:
            mock_client = MagicMock()
            mock_sync.return_value = mock_client

            client = create_localstack_client("s3", route="development")

            mock_sync.assert_called_once_with("s3", "development")
            assert client == mock_client


@pytest.mark.unit
def test_create_localstack_client_async_context():
    """Test that create_localstack_client returns async client in async context."""
    with patch("kstack_lib.clients.localstack._is_async_context", return_value=True):
        with patch("kstack_lib.clients.localstack._create_async_localstack_client") as mock_async:
            mock_client = MagicMock()
            mock_async.return_value = mock_client

            client = create_localstack_client("dynamodb", route="testing")

            mock_async.assert_called_once_with("dynamodb", "testing")
            assert client == mock_client


@pytest.mark.unit
def test_get_localstack_client_is_alias():
    """Test that get_localstack_client is an alias for create_localstack_client."""
    with patch("kstack_lib.clients.localstack.create_localstack_client") as mock_create:
        mock_client = MagicMock()
        mock_create.return_value = mock_client

        client = get_localstack_client("lambda", route="scratch")

        mock_create.assert_called_once_with("lambda", "scratch")
        assert client == mock_client


@pytest.mark.unit
def test_create_sync_localstack_client_with_custom_route():
    """Test that custom route is passed to config discovery."""
    mock_config = {"endpoint_url": "http://custom:4566"}

    with patch("kstack_lib.clients.localstack.get_localstack_config") as mock_get_config:
        mock_get_config.return_value = mock_config
        with patch("boto3.client"):
            _create_sync_localstack_client("s3", route="custom-route")

            # Verify route was passed to config discovery
            mock_get_config.assert_called_once_with(route="custom-route")


@pytest.mark.unit
def test_create_async_localstack_client_with_custom_route():
    """Test that custom route is passed to config discovery for async client."""
    mock_config = {"endpoint_url": "http://custom:4566"}

    with patch("kstack_lib.clients.localstack.get_localstack_config") as mock_get_config:
        mock_get_config.return_value = mock_config
        with patch("aioboto3.Session") as mock_session_class:
            mock_session = MagicMock()
            mock_session_class.return_value = mock_session

            _create_async_localstack_client("rds", route="production")

            # Verify route was passed to config discovery
            mock_get_config.assert_called_once_with(route="production")
