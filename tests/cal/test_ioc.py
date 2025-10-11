"""Tests for CAL IoC container.

Tests the Cloud Abstraction Layer dependency injection container,
following the same testing patterns as tests/test_container.py.
"""

from unittest.mock import MagicMock, patch

import pytest

from kstack_lib.cal.ioc import CALIoCContainer, create_cal_container, get_cal_container, reset_cal_container
from kstack_lib.config import ConfigMap
from kstack_lib.types import KStackEnvironment, KStackLayer


class TestCALIoCContainer:
    """Test CAL IoC container with dependency injection."""

    def test_container_creation(self):
        """Test creating a CAL IoC container."""
        cfg = ConfigMap(
            layer=KStackLayer.LAYER_3_GLOBAL_INFRA,
            environment=KStackEnvironment.DEVELOPMENT,
        )
        container = create_cal_container(cfg)

        # Container is created as DynamicContainer by dependency-injector
        assert container is not None
        assert container.config() is cfg

    def test_config_loader_is_singleton(self):
        """Test that config loader is a singleton."""
        cfg = ConfigMap(
            layer=KStackLayer.LAYER_3_GLOBAL_INFRA,
            environment=KStackEnvironment.DEVELOPMENT,
        )
        container = create_cal_container(cfg)

        loader1 = container.config_loader()
        loader2 = container.config_loader()

        # Should be same instance
        assert loader1 is loader2

    def test_provider_factory_is_singleton(self):
        """Test that provider factory is a singleton."""
        cfg = ConfigMap(
            layer=KStackLayer.LAYER_3_GLOBAL_INFRA,
            environment=KStackEnvironment.DEVELOPMENT,
        )
        container = create_cal_container(cfg)

        factory1 = container.provider_factory()
        factory2 = container.provider_factory()

        # Should be same instance
        assert factory1 is factory2

    def test_config_loader_override(self):
        """Test overriding config loader with a mock."""
        cfg = ConfigMap(
            layer=KStackLayer.LAYER_3_GLOBAL_INFRA,
            environment=KStackEnvironment.DEVELOPMENT,
        )
        container = create_cal_container(cfg)

        # Create mock loader
        mock_loader = MagicMock()
        mock_loader.return_value = ("mock_config", {"key": "value"})

        # Override
        container.config_loader.override(mock_loader)

        # Get loader
        loader = container.config_loader()

        # Should be the mock
        assert loader is mock_loader

        # Reset override
        container.config_loader.reset_override()

        # Should be back to original
        loader_after = container.config_loader()
        assert loader_after is not mock_loader

    def test_provider_factory_override(self):
        """Test overriding provider factory with a mock."""
        cfg = ConfigMap(
            layer=KStackLayer.LAYER_3_GLOBAL_INFRA,
            environment=KStackEnvironment.DEVELOPMENT,
        )
        container = create_cal_container(cfg)

        # Create mock factory
        mock_factory = MagicMock()
        mock_provider = MagicMock()
        mock_factory.return_value = mock_provider

        # Override
        container.provider_factory.override(mock_factory)

        # Get factory
        factory = container.provider_factory()

        # Should be the mock
        assert factory is mock_factory

        # Reset override
        container.provider_factory.reset_override()

        # Should be back to original
        factory_after = container.provider_factory()
        assert factory_after is not mock_factory

    def test_factory_kwargs_injection(self):
        """Test that factory kwargs are properly injected."""
        cfg = ConfigMap(
            layer=KStackLayer.LAYER_3_GLOBAL_INFRA,
            environment=KStackEnvironment.DEVELOPMENT,
        )
        container = create_cal_container(
            cfg,
            config_root="/custom/config",
            vault_root="/custom/vault",
        )

        factory_kwargs = container.factory_kwargs()

        assert factory_kwargs == {
            "config_root": "/custom/config",
            "vault_root": "/custom/vault",
        }


class TestGlobalCALContainer:
    """Test global CAL container singleton pattern."""

    def teardown_method(self):
        """Reset global container after each test."""
        reset_cal_container()

    def test_get_cal_container_creates_global(self):
        """Test that get_cal_container creates global container."""
        cfg = ConfigMap(
            layer=KStackLayer.LAYER_3_GLOBAL_INFRA,
            environment=KStackEnvironment.DEVELOPMENT,
        )

        container = get_cal_container(cfg)

        # Container is created as DynamicContainer by dependency-injector
        assert container is not None

    def test_get_cal_container_reuses_global(self):
        """Test that subsequent calls reuse global container."""
        cfg = ConfigMap(
            layer=KStackLayer.LAYER_3_GLOBAL_INFRA,
            environment=KStackEnvironment.DEVELOPMENT,
        )

        container1 = get_cal_container(cfg)
        container2 = get_cal_container()  # No config needed

        # Should be same instance
        assert container1 is container2

    def test_get_cal_container_requires_config_first_time(self):
        """Test that config is required on first call."""
        with pytest.raises(ValueError, match="config is required on first call"):
            get_cal_container()  # No config provided

    def test_reset_cal_container(self):
        """Test resetting global container."""
        cfg = ConfigMap(
            layer=KStackLayer.LAYER_3_GLOBAL_INFRA,
            environment=KStackEnvironment.DEVELOPMENT,
        )

        container1 = get_cal_container(cfg)
        reset_cal_container()

        # After reset, need config again
        with pytest.raises(ValueError, match="config is required on first call"):
            get_cal_container()

        # Create new global
        container2 = get_cal_container(cfg)

        # Should be different instance
        assert container1 is not container2


class TestCALIoCIntegration:
    """Integration tests for CAL IoC with real dependencies."""

    def test_config_loader_returns_real_function(self):
        """Test that config loader returns actual get_cloud_provider function."""
        cfg = ConfigMap(
            layer=KStackLayer.LAYER_3_GLOBAL_INFRA,
            environment=KStackEnvironment.DEVELOPMENT,
        )
        container = create_cal_container(cfg)

        loader = container.config_loader()

        # Should be the real function
        assert callable(loader)
        assert loader.__name__ == "get_cloud_provider"

    def test_provider_factory_returns_real_function(self):
        """Test that provider factory returns actual create_cloud_provider function."""
        cfg = ConfigMap(
            layer=KStackLayer.LAYER_3_GLOBAL_INFRA,
            environment=KStackEnvironment.DEVELOPMENT,
        )
        container = create_cal_container(cfg)

        factory = container.provider_factory()

        # Should be the real function
        assert callable(factory)
        assert factory.__name__ == "create_cloud_provider"

    @patch("kstack_lib.cal.ioc.get_cal_container")
    def test_container_is_mockable_in_tests(self, mock_get_container):
        """Test that global container can be mocked for testing."""
        # Setup mock
        mock_container = MagicMock(spec=CALIoCContainer)
        mock_get_container.return_value = mock_container

        # Import and use
        from kstack_lib.cal.ioc import get_cal_container

        container = get_cal_container()

        # Should be the mock
        assert container is mock_container
        mock_get_container.assert_called_once()
