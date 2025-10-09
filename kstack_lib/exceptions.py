"""
KStack exception classes.

This module defines custom exceptions for KStack to avoid masking built-in Python errors
and to provide clear, specific error handling for different failure scenarios.
"""


class KStackError(Exception):
    """
    Base exception for all KStack errors.

    All KStack exceptions inherit from this, allowing users to catch all KStack-specific
    errors with a single except clause while not catching unrelated Python errors.
    """

    pass


class LayerAccessError(KStackError):
    """
    Raised when trying to access a service from an invalid layer.

    Example:
    -------
        Trying to access Redis (Layer 3 service) from Layer 0:
        >>> cfg = ConfigMap(layer=KStackLayer.LAYER_0_APPLICATIONS)
        >>> get_redis_config(cfg, KStackRedisDatabase.PART_RAW)
        LayerAccessError: Redis databases are only available in Layer 3...

    """

    pass


class ServiceNotFoundError(KStackError):
    """
    Raised when a requested service configuration cannot be found.

    This indicates that the service exists and the layer is correct, but the
    configuration (vault file, K8s secret, etc.) is missing or inaccessible.

    Example:
    -------
        Redis service exists in Layer 3, but no config found for the route:
        >>> get_redis_config(cfg, KStackRedisDatabase.PART_RAW)
        ServiceNotFoundError: Redis configuration not found for route 'development'...

    """

    pass


class ConfigurationError(KStackError):
    """
    Raised when there is an error in KStack configuration.

    This includes malformed vault files, invalid layer definitions, etc.
    """

    pass


class RouteError(KStackError):
    """Raised when there is an error with route configuration or detection."""

    pass
