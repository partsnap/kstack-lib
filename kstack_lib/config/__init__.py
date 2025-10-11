"""KStack configuration management."""

from kstack_lib.config.cluster import KStackClusterConfig, get_active_environment
from kstack_lib.config.configmap import ConfigMap
from kstack_lib.config.loaders import (
    ConfigurationError,
    get_cloud_provider,
    load_cloud_credentials,
    load_environment_config,
    load_provider_config,
)
from kstack_lib.config.schemas import (
    CloudCredentials,
    EnvironmentConfig,
    ProviderConfig,
    ProviderCredentials,
    ProviderFamily,
    ProviderImplementation,
    ServiceConfig,
)
from kstack_lib.config.secrets import SecretsProvider, load_secrets_for_layer
from kstack_lib.types import (
    KStackEnvironment,
    KStackLayer,
    KStackLocalStackService,
    KStackRedisDatabase,
    LayerChoice,
)

__all__ = [
    "ConfigMap",
    "KStackLayer",
    "KStackEnvironment",
    "LayerChoice",
    "KStackRedisDatabase",
    "KStackLocalStackService",
    "SecretsProvider",
    "load_secrets_for_layer",
    # Cloud provider abstraction exports
    "CloudCredentials",
    "ConfigurationError",
    "EnvironmentConfig",
    "ProviderConfig",
    "ProviderCredentials",
    "ProviderFamily",
    "ProviderImplementation",
    "ServiceConfig",
    "get_cloud_provider",
    "load_cloud_credentials",
    "load_environment_config",
    "load_provider_config",
    # Cluster configuration exports
    "KStackClusterConfig",
    "get_active_environment",
]
