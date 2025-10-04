"""KStack configuration management."""

from kstack_lib.config.localstack import LocalStackDiscovery, get_localstack_config
from kstack_lib.config.redis import RedisDiscovery, get_redis_config

__all__ = ["LocalStackDiscovery", "RedisDiscovery", "get_localstack_config", "get_redis_config"]
