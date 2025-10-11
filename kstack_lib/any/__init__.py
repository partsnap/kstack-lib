"""
Any - Context-agnostic components for KStack.

This module contains code that works in BOTH cluster and local contexts.
It defines protocols, exceptions, types, and utilities used throughout kstack-lib.
"""

from kstack_lib.any.cloud_sessions import Boto3SessionFactory
from kstack_lib.any.container import (
    KStackIoCContainer,
    container,
    get_cloud_session_factory,
    get_environment_detector,
    get_secrets_provider,
    get_vault_manager,
)
from kstack_lib.any.context import is_in_cluster
from kstack_lib.any.exceptions import (
    KStackConfigurationError,
    KStackEnvironmentError,
    KStackError,
    KStackLayerAccessError,
    KStackRouteError,
    KStackServiceNotFoundError,
)
from kstack_lib.any.protocols import (
    CloudSessionFactory,
    ConfigProvider,
    EnvironmentDetector,
    SecretsProvider,
    VaultManager,
)

# Re-export types from any/types/
from kstack_lib.any.types import (
    KStackEnvironment,
    KStackLayer,
    KStackRedisDatabase,
)
from kstack_lib.any.utils import run_command

__all__ = [
    # Context detection
    "is_in_cluster",
    # Exceptions
    "KStackError",
    "KStackLayerAccessError",
    "KStackServiceNotFoundError",
    "KStackConfigurationError",
    "KStackRouteError",
    "KStackEnvironmentError",
    # Protocols
    "EnvironmentDetector",
    "SecretsProvider",
    "ConfigProvider",
    "VaultManager",
    "CloudSessionFactory",
    # Types
    "KStackLayer",
    "KStackEnvironment",
    "KStackRedisDatabase",
    # Utils
    "run_command",
    # DI Container
    "KStackIoCContainer",
    "container",
    "get_environment_detector",
    "get_secrets_provider",
    "get_vault_manager",
    "get_cloud_session_factory",
    # Cloud Sessions
    "Boto3SessionFactory",
]
