"""
KStack Library - Infrastructure client library for PartSnap services.

This library provides reusable components for connecting to PartSnap infrastructure:
- Redis client factories with automatic route discovery
- LocalStack client factories for AWS service emulation
- Configuration management from vault files and Kubernetes secrets

Designed to be used by Layer 2 services (like PartFinder) to connect to Layer 3 infrastructure.
"""

from kstack_lib.clients.redis import create_redis_client, get_redis_client
from kstack_lib.config.localstack import LocalStackDiscovery, get_localstack_config
from kstack_lib.config.redis import RedisConfig, RedisDiscovery, get_redis_config

try:
    from kstack_lib._version import __version__
except ImportError:
    __version__ = "0.0.0.dev0"

__all__ = [
    # Redis
    "create_redis_client",
    "get_redis_client",
    "RedisConfig",
    "RedisDiscovery",
    "get_redis_config",
    # LocalStack
    "LocalStackDiscovery",
    "get_localstack_config",
    # Version
    "__version__",
]
