# Configuration API Reference

API documentation for configuration discovery.

## Secrets Management

::: kstack_lib.config.secrets.SecretsProvider
options:
show_root_heading: true
show_source: true
members: - **init** - get_current_environment - get_current_namespace - is_running_in_k8s - load_secrets_from_vault - load_secrets_from_k8s - load_secrets - export_as_env_vars

::: kstack_lib.config.secrets.load_secrets_for_layer
options:
show_root_heading: true
show_source: true

## Redis Configuration

::: kstack_lib.config.redis.RedisDiscovery
options:
show_root_heading: true
show_source: true
members: - get_active_route - get_redis_config

::: kstack_lib.config.redis.get_redis_config
options:
show_root_heading: true
show_source: true

## LocalStack Configuration

::: kstack_lib.config.localstack.LocalStackDiscovery
options:
show_root_heading: true
show_source: true
members: - get_active_route - get_localstack_config

::: kstack_lib.config.localstack.get_localstack_config
options:
show_root_heading: true
show_source: true
