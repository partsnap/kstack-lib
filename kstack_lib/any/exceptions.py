"""
KStack exception classes.

This module defines custom exceptions for KStack to avoid masking built-in Python errors
and to provide clear, specific error handling for different failure scenarios.

All KStack exceptions follow the naming convention KStack*Error.
"""


class KStackError(Exception):
    """
    Base exception for all KStack errors.

    All KStack exceptions inherit from this, allowing users to catch all KStack-specific
    errors with a single except clause while not catching unrelated Python errors.
    """

    pass


class KStackLayerAccessError(KStackError):
    """
    Raised when trying to access a service from an invalid layer.

    Example:
    -------
        Trying to access Redis (Layer 3 service) from Layer 0:
        >>> cfg = ConfigMap(layer=KStackLayer.LAYER_0_APPLICATIONS)
        >>> get_redis_config(cfg, KStackRedisDatabase.PART_RAW)
        KStackLayerAccessError: Redis databases are only available in Layer 3...

    """

    pass


class KStackServiceNotFoundError(KStackError):
    """
    Raised when a requested service configuration cannot be found.

    This indicates that the service exists and the layer is correct, but the
    configuration (vault file, K8s secret, etc.) is missing or inaccessible.

    Example:
    -------
        Redis service exists in Layer 3, but no config found for the route:
        >>> get_redis_config(cfg, KStackRedisDatabase.PART_RAW)
        KStackServiceNotFoundError: Redis configuration not found for route 'development'...

    """

    pass


class KStackConfigurationError(KStackError):
    """
    Raised when there is an error in KStack configuration.

    This includes malformed vault files, invalid layer definitions, etc.
    """

    pass


class KStackRouteError(KStackError):
    """Raised when there is an error with route configuration or detection."""

    pass


class KStackEnvironmentError(KStackError):
    """
    Raised when code is imported or executed in the wrong environment context.

    This enforces the cluster/local separation:
    - Cluster-only code imported outside Kubernetes
    - Local-only code imported inside Kubernetes

    Example:
    -------
        >>> from kstack_lib.local.security import KStackVault  # In K8s cluster
        KStackEnvironmentError: Cannot import local module inside Kubernetes cluster

        >>> from kstack_lib.cluster.security import KubernetesSecretsAdapter  # On dev machine
        KStackEnvironmentError: Cannot import cluster module outside Kubernetes cluster

    """

    pass
