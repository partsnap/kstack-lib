"""
Cloud Provider Factory.

This module provides the factory function for creating cloud provider instances
based on configuration. It handles:

- Provider family detection (AWS, GCP, Azure, etc.)
- Adapter selection and instantiation
- Configuration and credential injection
- Provider-agnostic interface

Usage:
------
    >>> from kstack_lib.cal.factory import create_cloud_provider
    >>> from kstack_lib.config import ConfigMap, KStackLayer, KStackEnvironment
    >>>
    >>> cfg = ConfigMap(
    ...     layer=KStackLayer.LAYER_3_GLOBAL_INFRA,
    ...     environment=KStackEnvironment.DEVELOPMENT
    ... )
    >>> provider = create_cloud_provider(cfg, service="s3")
    >>> storage = provider.create_object_storage()
    >>> storage.list_buckets()

"""

from typing import Any

from kstack_lib.cal.adapters.aws_family import AWSFamilyProvider
from kstack_lib.cal.protocols import CloudProviderProtocol
from kstack_lib.config import ConfigMap
from kstack_lib.config.loaders import get_cloud_provider as get_cloud_config
from kstack_lib.config.schemas import ProviderFamily


class UnsupportedProviderError(Exception):
    """Raised when attempting to use an unsupported cloud provider."""

    pass


def create_cloud_provider(
    config: ConfigMap,
    service: str = "s3",
    override_provider: str | None = None,
    **kwargs: Any,
) -> CloudProviderProtocol:
    """
    Create a cloud provider instance based on configuration.

    This factory function:
    1. Loads provider configuration and credentials from vault
    2. Determines the provider family (AWS, GCP, Azure, etc.)
    3. Selects the appropriate adapter implementation
    4. Returns a configured provider instance

    Args:
    ----
        config: ConfigMap with layer and environment settings
        service: Service name to get provider for (s3, sqs, secretsmanager)
        override_provider: Optional provider name to override environment default
        **kwargs: Additional arguments passed to config loaders (config_root, vault_root)

    Returns:
    -------
        CloudProviderProtocol: Configured provider instance

    Raises:
    ------
        UnsupportedProviderError: If provider family is not supported
        ConfigurationError: If configuration or credentials are invalid

    Example:
    -------
        >>> # Get LocalStack provider for development
        >>> cfg = ConfigMap(
        ...     layer=KStackLayer.LAYER_3_GLOBAL_INFRA,
        ...     environment=KStackEnvironment.DEVELOPMENT
        ... )
        >>> provider = create_cloud_provider(cfg)
        >>>
        >>> # Get AWS provider with override
        >>> provider = create_cloud_provider(cfg, override_provider="aws-prod")
        >>>
        >>> # Use with context manager
        >>> with create_cloud_provider(cfg) as provider:
        ...     storage = provider.create_object_storage()
        ...     buckets = storage.list_buckets()

    """
    # Load provider configuration and credentials
    provider_config, credentials = get_cloud_config(
        config,
        service=service,
        override_provider=override_provider,
        **kwargs,
    )

    # Select adapter based on provider family
    if provider_config.provider_family == ProviderFamily.AWS:
        # AWS family includes: LocalStack, AWS, DigitalOcean Spaces, MinIO
        return AWSFamilyProvider(
            config=provider_config,
            credentials=credentials,
        )
    elif provider_config.provider_family == ProviderFamily.GCP:
        raise UnsupportedProviderError(
            "GCP provider family not yet implemented. " "Coming in a future phase of the cloud abstraction layer."
        )
    elif provider_config.provider_family == ProviderFamily.AZURE:
        raise UnsupportedProviderError(
            "Azure provider family not yet implemented. " "Coming in a future phase of the cloud abstraction layer."
        )
    else:
        raise UnsupportedProviderError(
            f"Unknown provider family: {provider_config.provider_family}. "
            f"Supported families: AWS (includes LocalStack, DigitalOcean, MinIO), "
            f"GCP (coming soon), Azure (coming soon)"
        )


def create_cloud_provider_from_config(
    provider_config: Any,
    credentials: dict[str, str],
) -> CloudProviderProtocol:
    """
    Create a cloud provider instance from explicit configuration.

    This is a lower-level factory function that takes explicit configuration
    instead of using ConfigMap. Useful for testing or custom configurations.

    Args:
    ----
        provider_config: ProviderConfig instance
        credentials: Credentials dictionary

    Returns:
    -------
        CloudProviderProtocol: Configured provider instance

    Raises:
    ------
        UnsupportedProviderError: If provider family is not supported

    Example:
    -------
        >>> from kstack_lib.config.loaders import load_provider_config
        >>> provider_cfg = load_provider_config("localstack", ...)
        >>> creds = {"aws_access_key_id": "test", "aws_secret_access_key": "test"}
        >>> provider = create_cloud_provider_from_config(provider_cfg, creds)

    """
    if provider_config.provider_family == ProviderFamily.AWS:
        # AWS family includes: LocalStack, AWS, DigitalOcean Spaces, MinIO
        return AWSFamilyProvider(
            config=provider_config,
            credentials=credentials,
        )
    elif provider_config.provider_family == ProviderFamily.GCP:
        raise UnsupportedProviderError("GCP provider family not yet implemented")
    elif provider_config.provider_family == ProviderFamily.AZURE:
        raise UnsupportedProviderError("Azure provider family not yet implemented")
    else:
        raise UnsupportedProviderError(f"Provider family {provider_config.provider_family} not yet supported")
