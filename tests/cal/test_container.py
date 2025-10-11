"""Tests for CAL CloudContainer with IoC integration.

Tests the Cloud Abstraction Layer container to ensure proper IoC integration,
following the same testing patterns as tests/test_container.py.
"""

from unittest.mock import MagicMock, Mock

import pytest

from kstack_lib.cal import CloudContainer
from kstack_lib.cal.protocols import CloudProviderProtocol, ObjectStorageProtocol, QueueProtocol
from kstack_lib.config import ConfigMap
from kstack_lib.types import KStackEnvironment, KStackLayer


class TestCloudContainerIoC:
    """Test CloudContainer with IoC integration."""

    def test_container_creates_ioc_internally(self):
        """Test that CloudContainer creates CAL IoC container internally."""
        cfg = ConfigMap(
            layer=KStackLayer.LAYER_3_GLOBAL_INFRA,
            environment=KStackEnvironment.DEVELOPMENT,
        )
        container = CloudContainer(cfg)

        # Should have IoC container
        assert hasattr(container, "_ioc")
        assert container._ioc is not None

        container.close()

    def test_container_passes_factory_kwargs_to_ioc(self):
        """Test that factory kwargs are passed to IoC container."""
        cfg = ConfigMap(
            layer=KStackLayer.LAYER_3_GLOBAL_INFRA,
            environment=KStackEnvironment.DEVELOPMENT,
        )
        container = CloudContainer(
            cfg,
            config_root="/custom/config",
            vault_root="/custom/vault",
        )

        # Check factory kwargs in IoC
        factory_kwargs = container._ioc.factory_kwargs()
        assert factory_kwargs["config_root"] == "/custom/config"
        assert factory_kwargs["vault_root"] == "/custom/vault"

        container.close()

    def test_provider_caching(self):
        """Test that providers are cached and reused."""
        cfg = ConfigMap(
            layer=KStackLayer.LAYER_3_GLOBAL_INFRA,
            environment=KStackEnvironment.DEVELOPMENT,
        )
        container = CloudContainer(cfg)

        # Mock the IoC provider factory
        mock_provider = MagicMock(spec=CloudProviderProtocol)
        mock_storage = MagicMock(spec=ObjectStorageProtocol)
        mock_provider.create_object_storage.return_value = mock_storage

        mock_factory = Mock(return_value=mock_provider)
        container._ioc.provider_factory.override(mock_factory)

        # First call should create provider
        storage1 = container.object_storage()
        assert storage1 is mock_storage
        assert mock_factory.call_count == 1

        # Second call should reuse cached provider
        storage2 = container.object_storage()
        assert storage2 is mock_storage
        assert mock_factory.call_count == 1  # Not called again

        container.close()

    def test_different_services_create_different_providers(self):
        """Test that different services create different providers."""
        cfg = ConfigMap(
            layer=KStackLayer.LAYER_3_GLOBAL_INFRA,
            environment=KStackEnvironment.DEVELOPMENT,
        )
        container = CloudContainer(cfg)

        # Mock the IoC provider factory
        mock_s3_provider = MagicMock(spec=CloudProviderProtocol)
        mock_sqs_provider = MagicMock(spec=CloudProviderProtocol)
        mock_storage = MagicMock(spec=ObjectStorageProtocol)
        mock_queue = MagicMock(spec=QueueProtocol)

        mock_s3_provider.create_object_storage.return_value = mock_storage
        mock_sqs_provider.create_queue.return_value = mock_queue

        call_count = 0

        def factory_side_effect(*args, **kwargs):
            nonlocal call_count
            call_count += 1
            if kwargs.get("service") == "s3":
                return mock_s3_provider
            elif kwargs.get("service") == "sqs":
                return mock_sqs_provider
            raise ValueError(f"Unexpected service: {kwargs.get('service')}")

        mock_factory = Mock(side_effect=factory_side_effect)
        container._ioc.provider_factory.override(mock_factory)

        # Get different services
        storage = container.object_storage()
        queue = container.queue()

        # Should have created two different providers
        assert call_count == 2
        assert storage is mock_storage
        assert queue is mock_queue

        container.close()

    def test_provider_override_per_service(self):
        """Test that provider can be overridden per service."""
        cfg = ConfigMap(
            layer=KStackLayer.LAYER_3_GLOBAL_INFRA,
            environment=KStackEnvironment.DEVELOPMENT,
        )
        container = CloudContainer(cfg)

        # Mock the IoC provider factory
        mock_default_provider = MagicMock(spec=CloudProviderProtocol)
        mock_aws_provider = MagicMock(spec=CloudProviderProtocol)
        mock_default_storage = MagicMock(spec=ObjectStorageProtocol)
        mock_aws_storage = MagicMock(spec=ObjectStorageProtocol)

        mock_default_provider.create_object_storage.return_value = mock_default_storage
        mock_aws_provider.create_object_storage.return_value = mock_aws_storage

        def factory_side_effect(*args, **kwargs):
            if kwargs.get("override_provider") == "aws-prod":
                return mock_aws_provider
            return mock_default_provider

        mock_factory = Mock(side_effect=factory_side_effect)
        container._ioc.provider_factory.override(mock_factory)

        # Get default storage
        default_storage = container.object_storage()
        assert default_storage is mock_default_storage

        # Get AWS-specific storage
        aws_storage = container.object_storage(provider="aws-prod")
        assert aws_storage is mock_aws_storage

        # Should have two cached providers
        assert len(container._providers) == 2

        container.close()

    def test_container_close_cleans_up_providers(self):
        """Test that closing container cleans up all providers."""
        cfg = ConfigMap(
            layer=KStackLayer.LAYER_3_GLOBAL_INFRA,
            environment=KStackEnvironment.DEVELOPMENT,
        )
        container = CloudContainer(cfg)

        # Mock providers
        mock_provider1 = MagicMock(spec=CloudProviderProtocol)
        mock_provider2 = MagicMock(spec=CloudProviderProtocol)
        mock_storage = MagicMock(spec=ObjectStorageProtocol)
        mock_queue = MagicMock(spec=QueueProtocol)

        mock_provider1.create_object_storage.return_value = mock_storage
        mock_provider2.create_queue.return_value = mock_queue

        call_count = 0

        def factory_side_effect(*args, **kwargs):
            nonlocal call_count
            call_count += 1
            if call_count == 1:
                return mock_provider1
            return mock_provider2

        mock_factory = Mock(side_effect=factory_side_effect)
        container._ioc.provider_factory.override(mock_factory)

        # Create multiple services
        container.object_storage()
        container.queue()

        # Close container
        container.close()

        # Both providers should be closed
        mock_provider1.close.assert_called_once()
        mock_provider2.close.assert_called_once()

        # Cache should be cleared
        assert len(container._providers) == 0

        # Container should be marked closed
        assert container._closed is True

    def test_closed_container_raises_error(self):
        """Test that using closed container raises error."""
        cfg = ConfigMap(
            layer=KStackLayer.LAYER_3_GLOBAL_INFRA,
            environment=KStackEnvironment.DEVELOPMENT,
        )
        container = CloudContainer(cfg)
        container.close()

        with pytest.raises(RuntimeError, match="Container has been closed"):
            container.object_storage()

    def test_context_manager_cleanup(self):
        """Test that context manager properly cleans up."""
        cfg = ConfigMap(
            layer=KStackLayer.LAYER_3_GLOBAL_INFRA,
            environment=KStackEnvironment.DEVELOPMENT,
        )

        mock_provider = MagicMock(spec=CloudProviderProtocol)
        mock_storage = MagicMock(spec=ObjectStorageProtocol)
        mock_provider.create_object_storage.return_value = mock_storage

        with CloudContainer(cfg) as container:
            # Mock factory
            mock_factory = Mock(return_value=mock_provider)
            container._ioc.provider_factory.override(mock_factory)

            # Use container
            storage = container.object_storage()
            assert storage is mock_storage

        # After exit, provider should be closed
        mock_provider.close.assert_called_once()

    @pytest.mark.asyncio
    async def test_async_context_manager_cleanup(self):
        """Test that async context manager properly cleans up."""
        cfg = ConfigMap(
            layer=KStackLayer.LAYER_3_GLOBAL_INFRA,
            environment=KStackEnvironment.DEVELOPMENT,
        )

        mock_provider = MagicMock(spec=CloudProviderProtocol)
        mock_queue = MagicMock(spec=QueueProtocol)
        mock_provider.create_queue.return_value = mock_queue

        async with CloudContainer(cfg) as container:
            # Mock factory
            mock_factory = Mock(return_value=mock_provider)
            container._ioc.provider_factory.override(mock_factory)

            # Use container
            queue = container.queue()
            assert queue is mock_queue

        # After exit, provider should be closed
        mock_provider.close.assert_called_once()


class TestCloudContainerConsistency:
    """Test consistency of CloudContainer with main IoC container patterns."""

    def test_injectable_config_loader(self):
        """Test that config loader can be injected via IoC."""
        cfg = ConfigMap(
            layer=KStackLayer.LAYER_3_GLOBAL_INFRA,
            environment=KStackEnvironment.DEVELOPMENT,
        )
        container = CloudContainer(cfg)

        # Mock config loader
        mock_loader = Mock(return_value=("mock_provider", {"key": "value"}))
        container._ioc.config_loader.override(mock_loader)

        # Get loader from IoC
        loader = container._ioc.config_loader()
        assert loader is mock_loader

        container.close()

    def test_injectable_provider_factory(self):
        """Test that provider factory can be injected via IoC."""
        cfg = ConfigMap(
            layer=KStackLayer.LAYER_3_GLOBAL_INFRA,
            environment=KStackEnvironment.DEVELOPMENT,
        )
        container = CloudContainer(cfg)

        # Mock factory
        mock_factory = Mock()
        container._ioc.provider_factory.override(mock_factory)

        # Get factory from IoC
        factory = container._ioc.provider_factory()
        assert factory is mock_factory

        container.close()

    def test_ioc_singletons(self):
        """Test that IoC components are singletons."""
        cfg = ConfigMap(
            layer=KStackLayer.LAYER_3_GLOBAL_INFRA,
            environment=KStackEnvironment.DEVELOPMENT,
        )
        container = CloudContainer(cfg)

        # Get loader twice
        loader1 = container._ioc.config_loader()
        loader2 = container._ioc.config_loader()
        assert loader1 is loader2

        # Get factory twice
        factory1 = container._ioc.provider_factory()
        factory2 = container._ioc.provider_factory()
        assert factory1 is factory2

        container.close()

    def test_ioc_override_reset(self):
        """Test that IoC overrides can be reset."""
        cfg = ConfigMap(
            layer=KStackLayer.LAYER_3_GLOBAL_INFRA,
            environment=KStackEnvironment.DEVELOPMENT,
        )
        container = CloudContainer(cfg)

        # Get original factory
        original_factory = container._ioc.provider_factory()

        # Override with mock
        mock_factory = Mock()
        container._ioc.provider_factory.override(mock_factory)
        assert container._ioc.provider_factory() is mock_factory

        # Reset override
        container._ioc.provider_factory.reset_override()
        after_reset = container._ioc.provider_factory()
        assert after_reset is original_factory
        assert after_reset is not mock_factory

        container.close()


class TestCloudContainerBackwardCompatibility:
    """Test that CloudContainer maintains backward compatibility."""

    def test_default_provider_parameter(self):
        """Test that default_provider parameter works."""
        cfg = ConfigMap(
            layer=KStackLayer.LAYER_3_GLOBAL_INFRA,
            environment=KStackEnvironment.DEVELOPMENT,
        )
        container = CloudContainer(cfg, default_provider="aws-prod")

        assert container._default_provider == "aws-prod"

        container.close()

    def test_factory_kwargs_parameter(self):
        """Test that factory kwargs are stored."""
        cfg = ConfigMap(
            layer=KStackLayer.LAYER_3_GLOBAL_INFRA,
            environment=KStackEnvironment.DEVELOPMENT,
        )
        container = CloudContainer(
            cfg,
            config_root="/custom",
            vault_root="/vault",
        )

        assert container._factory_kwargs["config_root"] == "/custom"
        assert container._factory_kwargs["vault_root"] == "/vault"

        container.close()

    def test_public_api_unchanged(self):
        """Test that public API methods are unchanged."""
        cfg = ConfigMap(
            layer=KStackLayer.LAYER_3_GLOBAL_INFRA,
            environment=KStackEnvironment.DEVELOPMENT,
        )
        container = CloudContainer(cfg)

        # Public methods should exist
        assert hasattr(container, "object_storage")
        assert hasattr(container, "queue")
        assert hasattr(container, "secret_manager")
        assert hasattr(container, "close")
        assert hasattr(container, "__enter__")
        assert hasattr(container, "__exit__")
        assert hasattr(container, "__aenter__")
        assert hasattr(container, "__aexit__")

        container.close()
