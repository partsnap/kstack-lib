"""
Cloud Abstraction Layer Dependency Injection Container.

This module provides a dependency injection container for cloud services that:
- Manages provider lifecycle (creation, caching, cleanup)
- Integrates with ConfigMap for automatic configuration
- Provides lazy initialization of cloud clients
- Handles context management and resource cleanup
- Uses IoC pattern for consistent dependency injection

Usage:
------
    >>> from kstack_lib.cal.container import CloudContainer
    >>> from kstack_lib.config import ConfigMap, KStackLayer, KStackEnvironment
    >>>
    >>> # Create container with config
    >>> cfg = ConfigMap(
    ...     layer=KStackLayer.LAYER_3_GLOBAL_INFRA,
    ...     environment=KStackEnvironment.DEVELOPMENT
    ... )
    >>> container = CloudContainer(cfg)
    >>>
    >>> # Get cloud services
    >>> storage = container.object_storage()
    >>> queue = container.queue()
    >>>
    >>> # Cleanup when done
    >>> container.close()
    >>>
    >>> # Or use context manager
    >>> with CloudContainer(cfg) as container:
    ...     storage = container.object_storage()
    ...     buckets = storage.list_buckets()

"""

from typing import Any

from kstack_lib.cal.ioc import create_cal_container
from kstack_lib.cal.protocols import (
    CloudProviderProtocol,
    ObjectStorageProtocol,
    QueueProtocol,
    SecretManagerProtocol,
)
from kstack_lib.config import ConfigMap


class CloudContainer:
    """
    Dependency injection container for cloud services.

    This container manages the lifecycle of cloud provider instances and
    provides easy access to cloud services. It uses the CAL IoC container
    internally for consistent dependency injection patterns.

    Features:
    - Lazy initialization (providers created on first use)
    - Service caching (single provider instance per service)
    - Automatic cleanup via context managers
    - ConfigMap integration for seamless configuration
    - IoC-based provider factories (testable/mockable)

    Example:
    -------
        >>> # Basic usage
        >>> cfg = ConfigMap(layer=KStackLayer.LAYER_3_GLOBAL_INFRA)
        >>> container = CloudContainer(cfg)
        >>> storage = container.object_storage()
        >>> buckets = storage.list_buckets()
        >>> container.close()
        >>>
        >>> # Context manager usage
        >>> with CloudContainer(cfg) as container:
        ...     storage = container.object_storage()
        ...     queue = container.queue()
        ...
        >>> # Provider override
        >>> container = CloudContainer(cfg, default_provider="aws-prod")

    """

    def __init__(
        self,
        config: ConfigMap,
        default_provider: str | None = None,
        **factory_kwargs: Any,
    ):
        """
        Initialize the cloud container.

        Args:
        ----
            config: ConfigMap with layer and environment settings
            default_provider: Optional provider name to use by default
            **factory_kwargs: Additional arguments for create_cloud_provider
                            (e.g., config_root, vault_root)

        """
        self._config = config
        self._default_provider = default_provider
        self._factory_kwargs = factory_kwargs

        # Create IoC container for dependency injection
        self._ioc = create_cal_container(config, **factory_kwargs)

        # Cache for cloud providers (one per service)
        self._providers: dict[str, CloudProviderProtocol] = {}
        self._closed = False

    def _get_provider(self, service: str, provider: str | None = None) -> CloudProviderProtocol:
        """
        Get or create a provider for the specified service.

        This method uses the IoC container's provider factory for creating
        providers, enabling testability and consistent DI patterns.

        Args:
        ----
            service: Service name (s3, sqs, secretsmanager)
            provider: Optional provider override

        Returns:
        -------
            CloudProviderProtocol instance

        """
        if self._closed:
            raise RuntimeError("Container has been closed")

        # Use provided override, or default override, or environment default
        provider_key = provider or self._default_provider or f"{service}_default"

        # Return cached provider if available
        if provider_key in self._providers:
            return self._providers[provider_key]

        # Create new provider using IoC container's factory
        factory = self._ioc.provider_factory()
        cloud_provider = factory(
            config=self._config,
            service=service,
            override_provider=provider or self._default_provider,
            **self._factory_kwargs,
        )

        # Cache for reuse
        self._providers[provider_key] = cloud_provider

        return cloud_provider

    def object_storage(self, provider: str | None = None) -> ObjectStorageProtocol:
        """
        Get an object storage client.

        Args:
        ----
            provider: Optional provider override for this service

        Returns:
        -------
            ObjectStorageProtocol implementation

        Example:
        -------
            >>> container = CloudContainer(cfg)
            >>> storage = container.object_storage()
            >>> storage.list_buckets()
            >>> # Use specific provider
            >>> aws_storage = container.object_storage(provider="aws-prod")

        """
        cloud_provider = self._get_provider("s3", provider)
        return cloud_provider.create_object_storage()

    def queue(self, provider: str | None = None) -> QueueProtocol:
        """
        Get a message queue client.

        Args:
        ----
            provider: Optional provider override for this service

        Returns:
        -------
            QueueProtocol implementation

        Example:
        -------
            >>> container = CloudContainer(cfg)
            >>> queue_client = container.queue()
            >>> queue_url = queue_client.create_queue("my-queue")

        """
        cloud_provider = self._get_provider("sqs", provider)
        return cloud_provider.create_queue()

    def secret_manager(self, provider: str | None = None) -> SecretManagerProtocol:
        """
        Get a secrets manager client.

        Args:
        ----
            provider: Optional provider override for this service

        Returns:
        -------
            SecretManagerProtocol implementation

        Example:
        -------
            >>> container = CloudContainer(cfg)
            >>> secrets = container.secret_manager()
            >>> arn = secrets.create_secret("my-secret", "secret-value")

        Note:
        ----
            TODO: This provides AWS Secrets Manager API access for runtime
            application secrets. This is separate from:
            1. partsecrets (age-encrypted vault for config/credentials at rest)
            2. Kubernetes External Secrets (syncing cloud secrets to K8s)

            We should revisit the secret management architecture to better
            unify these three layers in a future phase.

        """
        cloud_provider = self._get_provider("secretsmanager", provider)
        return cloud_provider.create_secret_manager()

    def close(self) -> None:
        """
        Close all providers and cleanup resources.

        This should be called when the container is no longer needed.
        After calling close(), the container cannot be used anymore.
        """
        if self._closed:
            return

        for provider in self._providers.values():
            provider.close()

        self._providers.clear()
        self._closed = True

    def __enter__(self) -> "CloudContainer":
        """Context manager entry."""
        return self

    def __exit__(self, exc_type: Any, exc_val: Any, exc_tb: Any) -> None:
        """Context manager exit with cleanup."""
        self.close()

    async def __aenter__(self) -> "CloudContainer":
        """Async context manager entry."""
        return self

    async def __aexit__(self, exc_type: Any, exc_val: Any, exc_tb: Any) -> None:
        """Async context manager exit with cleanup."""
        self.close()

    def __del__(self) -> None:
        """Destructor to ensure cleanup even if close() not called."""
        if not self._closed:
            self.close()
