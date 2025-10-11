"""Tests for Boto3SessionFactory."""

import sys
from unittest.mock import MagicMock, Mock

import pytest

from kstack_lib.any.cloud_sessions import Boto3SessionFactory
from kstack_lib.any.exceptions import KStackConfigurationError


class TestBoto3SessionFactory:
    """Test Boto3SessionFactory class."""

    @pytest.fixture
    def mock_secrets_provider(self):
        """Create a mock secrets provider."""
        provider = MagicMock()
        provider.get_credentials.return_value = {
            "aws_access_key_id": "test_access_key",
            "aws_secret_access_key": "test_secret_key",
            "aws_region": "us-west-2",
            "endpoint_url": "http://localhost:4566",
        }
        return provider

    @pytest.fixture
    def factory(self, mock_secrets_provider):
        """Create a Boto3SessionFactory instance."""
        return Boto3SessionFactory(mock_secrets_provider)

    @pytest.fixture
    def mock_boto3(self):
        """Mock boto3 module."""
        mock = MagicMock()
        sys.modules["boto3"] = mock
        yield mock
        if "boto3" in sys.modules:
            del sys.modules["boto3"]

    @pytest.fixture
    def mock_aioboto3(self):
        """Mock aioboto3 module."""
        mock = MagicMock()
        sys.modules["aioboto3"] = mock
        yield mock
        if "aioboto3" in sys.modules:
            del sys.modules["aioboto3"]

    def test_init(self, mock_secrets_provider):
        """Test factory initialization."""
        factory = Boto3SessionFactory(mock_secrets_provider)

        assert factory._secrets == mock_secrets_provider

    def test_create_session_success(self, factory, mock_secrets_provider, mock_boto3):
        """Test successful boto3 session creation."""
        mock_session = MagicMock()
        mock_boto3.Session.return_value = mock_session

        result = factory.create_session("s3", "layer3", "dev")

        # Verify credentials were requested
        mock_secrets_provider.get_credentials.assert_called_once_with("s3", "layer3", "dev")

        # Verify boto3.Session was created with correct parameters
        mock_boto3.Session.assert_called_once_with(
            aws_access_key_id="test_access_key",
            aws_secret_access_key="test_secret_key",
            region_name="us-west-2",
        )

        assert result == mock_session

    def test_create_async_session_success(self, factory, mock_secrets_provider, mock_aioboto3):
        """Test successful aioboto3 session creation."""
        mock_session = MagicMock()
        mock_aioboto3.Session.return_value = mock_session

        result = factory.create_async_session("s3", "layer3", "dev")

        # Verify credentials were requested
        mock_secrets_provider.get_credentials.assert_called_once_with("s3", "layer3", "dev")

        # Verify aioboto3.Session was created with correct parameters
        mock_aioboto3.Session.assert_called_once_with(
            aws_access_key_id="test_access_key",
            aws_secret_access_key="test_secret_key",
            region_name="us-west-2",
        )

        assert result == mock_session

    def test_create_session_boto3_not_installed(self, factory):
        """Test error when boto3 is not installed."""
        # Ensure boto3 is not in sys.modules
        if "boto3" in sys.modules:
            del sys.modules["boto3"]

        # Mock import to raise ImportError
        import builtins

        real_import = builtins.__import__

        def mock_import(name, *args, **kwargs):
            if name == "boto3":
                raise ImportError("No module named 'boto3'")
            return real_import(name, *args, **kwargs)

        builtins.__import__ = mock_import
        try:
            with pytest.raises(KStackConfigurationError, match="boto3 not installed"):
                factory.create_session("s3", "layer3", "dev")
        finally:
            builtins.__import__ = real_import

    def test_create_async_session_aioboto3_not_installed(self, factory):
        """Test error when aioboto3 is not installed."""
        # Ensure aioboto3 is not in sys.modules
        if "aioboto3" in sys.modules:
            del sys.modules["aioboto3"]

        import builtins

        real_import = builtins.__import__

        def mock_import(name, *args, **kwargs):
            if name == "aioboto3":
                raise ImportError("No module named 'aioboto3'")
            return real_import(name, *args, **kwargs)

        builtins.__import__ = mock_import
        try:
            with pytest.raises(KStackConfigurationError, match="aioboto3 not installed"):
                factory.create_async_session("s3", "layer3", "dev")
        finally:
            builtins.__import__ = real_import

    def test_create_session_missing_access_key(self, factory, mock_secrets_provider, mock_boto3):
        """Test error when aws_access_key_id is missing."""
        mock_secrets_provider.get_credentials.return_value = {
            "aws_secret_access_key": "test_secret_key",
            "aws_region": "us-west-2",
        }

        with pytest.raises(
            KStackConfigurationError,
            match=r"Missing AWS credentials",
        ):
            factory.create_session("s3", "layer3", "dev")

    def test_create_session_missing_secret_key(self, factory, mock_secrets_provider, mock_boto3):
        """Test error when aws_secret_access_key is missing."""
        mock_secrets_provider.get_credentials.return_value = {
            "aws_access_key_id": "test_access_key",
            "aws_region": "us-west-2",
        }

        with pytest.raises(
            KStackConfigurationError,
            match=r"Missing AWS credentials",
        ):
            factory.create_session("s3", "layer3", "dev")

    def test_create_session_default_region(self, factory, mock_secrets_provider, mock_boto3):
        """Test default region when not specified in credentials."""
        mock_secrets_provider.get_credentials.return_value = {
            "aws_access_key_id": "test_access_key",
            "aws_secret_access_key": "test_secret_key",
            # No aws_region specified
        }
        mock_boto3.Session.return_value = MagicMock()

        factory.create_session("s3", "layer3", "dev")

        # Should use default region
        mock_boto3.Session.assert_called_once_with(
            aws_access_key_id="test_access_key",
            aws_secret_access_key="test_secret_key",
            region_name="us-east-1",  # Default
        )

    def test_create_async_session_missing_credentials(self, factory, mock_secrets_provider, mock_aioboto3):
        """Test error when credentials are missing for async session."""
        mock_secrets_provider.get_credentials.return_value = {
            "aws_region": "us-west-2",
            # Missing both access key and secret key
        }

        with pytest.raises(
            KStackConfigurationError,
            match=r"Missing AWS credentials",
        ):
            factory.create_async_session("s3", "layer3", "dev")

    def test_create_session_impl_directly(self, factory, mock_secrets_provider):
        """Test internal _create_session_impl method."""
        mock_session_factory = Mock(return_value="test_session")

        result = factory._create_session_impl(
            service="s3",
            layer="layer3",
            environment="dev",
            session_factory=mock_session_factory,
            library_name="test-lib",
        )

        # Verify credentials were requested
        mock_secrets_provider.get_credentials.assert_called_once_with("s3", "layer3", "dev")

        # Verify session factory was called
        mock_session_factory.assert_called_once_with(
            aws_access_key_id="test_access_key",
            aws_secret_access_key="test_secret_key",
            region_name="us-west-2",
        )

        assert result == "test_session"

    def test_create_session_impl_missing_credentials(self, factory, mock_secrets_provider):
        """Test _create_session_impl with missing credentials."""
        mock_secrets_provider.get_credentials.return_value = {
            "aws_region": "us-west-2",
        }
        mock_session_factory = Mock()

        with pytest.raises(
            KStackConfigurationError,
            match=r"Missing AWS credentials",
        ):
            factory._create_session_impl(
                service="s3",
                layer="layer3",
                environment="dev",
                session_factory=mock_session_factory,
                library_name="test-lib",
            )

        # Session factory should not be called
        mock_session_factory.assert_not_called()

    def test_repr(self, factory, mock_secrets_provider):
        """Test __repr__ method."""
        repr_str = repr(factory)

        assert "Boto3SessionFactory" in repr_str
        assert "secrets=" in repr_str

    def test_create_session_different_services(self, factory, mock_secrets_provider, mock_boto3):
        """Test creating sessions for different services."""
        services = ["s3", "dynamodb", "sqs", "sns"]
        mock_boto3.Session.return_value = MagicMock()

        for service in services:
            factory.create_session(service, "layer3", "dev")

            # Verify correct service was requested
            assert mock_secrets_provider.get_credentials.call_args[0][0] == service

    def test_create_session_different_layers(self, factory, mock_secrets_provider, mock_boto3):
        """Test creating sessions for different layers."""
        layers = ["layer0", "layer1", "layer2", "layer3"]
        mock_boto3.Session.return_value = MagicMock()

        for layer in layers:
            factory.create_session("s3", layer, "dev")

            # Verify correct layer was requested
            assert mock_secrets_provider.get_credentials.call_args[0][1] == layer

    def test_create_session_different_environments(self, factory, mock_secrets_provider, mock_boto3):
        """Test creating sessions for different environments."""
        environments = ["dev", "staging", "production"]
        mock_boto3.Session.return_value = MagicMock()

        for env in environments:
            factory.create_session("s3", "layer3", env)

            # Verify correct environment was requested
            assert mock_secrets_provider.get_credentials.call_args[0][2] == env

    def test_session_factory_callable_signature(self, factory, mock_secrets_provider):
        """Test that session factory receives correct parameters."""
        captured_kwargs = {}

        def mock_factory(**kwargs):
            captured_kwargs.update(kwargs)
            return MagicMock()

        factory._create_session_impl(
            service="s3",
            layer="layer3",
            environment="dev",
            session_factory=mock_factory,
            library_name="test",
        )

        assert captured_kwargs["aws_access_key_id"] == "test_access_key"
        assert captured_kwargs["aws_secret_access_key"] == "test_secret_key"
        assert captured_kwargs["region_name"] == "us-west-2"
        assert len(captured_kwargs) == 3  # No extra parameters
