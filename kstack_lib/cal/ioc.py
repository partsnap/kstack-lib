"""
Cloud Abstraction Layer IoC Container.

This module provides dependency injection for CAL components, following the same
pattern as kstack_lib.any.container for consistency.

The CAL IoC container manages:
- Configuration loaders (injectable for testing)
- Provider factories (injectable for testing)
- Provider caching (singleton pattern)
- Resource cleanup

Example:
-------
    ```python
    from kstack_lib.cal.ioc import get_cal_container
    from kstack_lib.config import ConfigMap, KStackLayer

    # Get provider via IoC
    cfg = ConfigMap(layer=KStackLayer.LAYER_3_GLOBAL_INFRA)
    container = get_cal_container(cfg)
    provider = container.cloud_provider("s3")

    # Get service directly
    storage = container.object_storage()
    ```

"""

from typing import Any

from dependency_injector import containers, providers

from kstack_lib.config import ConfigMap


class CALIoCContainer(containers.DeclarativeContainer):
    """
    Inversion of Control (IoC) container for Cloud Abstraction Layer.

    This container manages cloud provider lifecycle and dependency injection,
    following the same pattern as KStackIoCContainer for consistency.

    Features:
    - Injectable configuration loaders (mockable in tests)
    - Injectable provider factories (mockable in tests)
    - Singleton providers (created once per service)
    - Lazy loading of adapters
    - Type-safe dependency injection

    Example:
    -------
        ```python
        # Create container with config
        from kstack_lib.config import ConfigMap, KStackLayer
        cfg = ConfigMap(layer=KStackLayer.LAYER_3_GLOBAL_INFRA)
        container = CALIoCContainer(config=cfg)

        # Get cloud provider (singleton, cached)
        provider = container.cloud_provider("s3")

        # Get services directly
        storage = container.object_storage()
        queue = container.queue()

        # Override in tests
        container.config_loader.override(mock_loader)
        ```

    """

    # Configuration input (dependency)
    config = providers.Dependency(instance_of=ConfigMap)

    # Factory kwargs (optional overrides for config/vault paths)
    factory_kwargs = providers.Dict()

    # Configuration loader - loads provider config and credentials
    # Can be overridden in tests with mocks
    config_loader = providers.Singleton(
        providers.Callable(
            lambda: __import__(
                "kstack_lib.config.loaders",
                fromlist=["get_cloud_provider"],
            ).get_cloud_provider
        )
    )

    # Provider factory - creates cloud provider instances
    # Can be overridden in tests with mocks
    provider_factory = providers.Singleton(
        providers.Callable(
            lambda: __import__(
                "kstack_lib.cal.factory",
                fromlist=["create_cloud_provider"],
            ).create_cloud_provider
        )
    )

    # Provider cache - stores created providers for reuse
    # Using Factory instead of Singleton because we need multiple instances (one per service)
    _provider_cache = providers.Dict()


def create_cal_container(
    config: ConfigMap,
    **factory_kwargs: Any,
) -> CALIoCContainer:
    """
    Create a CAL IoC container with configuration.

    This is the recommended way to create CAL containers. It properly
    injects the config and factory kwargs.

    Args:
    ----
        config: ConfigMap with layer and environment settings
        **factory_kwargs: Optional overrides (config_root, vault_root)

    Returns:
    -------
        Configured CAL IoC container

    Example:
    -------
        ```python
        from kstack_lib.config import ConfigMap, KStackLayer
        from kstack_lib.cal.ioc import create_cal_container

        cfg = ConfigMap(layer=KStackLayer.LAYER_3_GLOBAL_INFRA)
        container = create_cal_container(cfg)

        # Get provider
        provider = container.provider_factory()(
            config=cfg,
            service="s3",
            **factory_kwargs
        )
        ```

    """
    container = CALIoCContainer()
    container.config.override(config)
    container.factory_kwargs.override(factory_kwargs)
    return container


# Global singleton container (can be overridden in tests)
_global_container: CALIoCContainer | None = None


def get_cal_container(config: ConfigMap | None = None, **kwargs: Any) -> CALIoCContainer:
    """
    Get or create the global CAL IoC container.

    This provides a global singleton container for convenience, similar to
    kstack_lib.any.container.container.

    Args:
    ----
        config: Optional ConfigMap (required on first call)
        **kwargs: Optional factory kwargs

    Returns:
    -------
        Global CAL IoC container

    Example:
    -------
        ```python
        from kstack_lib.config import ConfigMap, KStackLayer
        from kstack_lib.cal.ioc import get_cal_container

        cfg = ConfigMap(layer=KStackLayer.LAYER_3_GLOBAL_INFRA)

        # First call creates global container
        container = get_cal_container(cfg)

        # Subsequent calls return same instance
        same_container = get_cal_container()
        assert container is same_container
        ```

    """
    global _global_container

    if _global_container is None:
        if config is None:
            raise ValueError(
                "config is required on first call to get_cal_container(). "
                "Subsequent calls can omit it to reuse the global container."
            )
        _global_container = create_cal_container(config, **kwargs)

    return _global_container


def reset_cal_container() -> None:
    """
    Reset the global CAL container.

    This is primarily useful for testing to ensure a clean state
    between test cases.

    Example:
    -------
        ```python
        from kstack_lib.cal.ioc import reset_cal_container

        def teardown():
            reset_cal_container()  # Clean slate for next test
        ```

    """
    global _global_container
    _global_container = None
