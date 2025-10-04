# Configuration API Reference

API documentation for configuration discovery.

## Redis Configuration

::: kstack_lib.config.redis.RedisDiscovery
    options:
      show_root_heading: true
      show_source: true
      members:
        - get_active_route
        - get_redis_config

::: kstack_lib.config.redis.get_redis_config
    options:
      show_root_heading: true
      show_source: true

## LocalStack Configuration

::: kstack_lib.config.localstack.LocalStackDiscovery
    options:
      show_root_heading: true
      show_source: true
      members:
        - get_active_route
        - get_localstack_config

::: kstack_lib.config.localstack.get_localstack_config
    options:
      show_root_heading: true
      show_source: true
