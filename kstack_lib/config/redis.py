"""
Redis configuration discovery for KStack.

Automatically discovers Redis endpoints based on the active route and layer.
Applications use this to connect to the correct Redis instance without hardcoding credentials.

Example:
-------
    from kstack_lib.config import ConfigMap, get_redis_config
    from kstack_lib.types import KStackLayer, KStackRedisDatabase

    # Create ConfigMap for your layer
    cfg = ConfigMap(layer=KStackLayer.LAYER_3_GLOBAL_INFRA)

    # Get Redis configuration with type safety
    config = get_redis_config(cfg, KStackRedisDatabase.PART_RAW)
    redis_client = Redis(
        host=config['host'],
        port=config['port'],
        username=config['username'],
        password=config['password']
    )

"""

import os
import subprocess
from pathlib import Path
from typing import TYPE_CHECKING, Literal, TypedDict

import yaml

from kstack_lib.exceptions import LayerAccessError, ServiceNotFoundError

if TYPE_CHECKING:
    from kstack_lib.config.configmap import ConfigMap
    from kstack_lib.types import KStackRedisDatabase


class RedisConfig(TypedDict):
    """Redis connection configuration."""

    host: str
    port: int
    username: str
    password: str


class RedisDiscovery:
    """Discovers Redis configuration based on active KStack route."""

    def __init__(self) -> None:
        """Initialize RedisDiscovery."""
        self.kstack_root = Path(__file__).parent.parent.parent
        self.vault_dir = self.kstack_root / "vault" / "dev"

    def get_current_namespace(self) -> str:
        """
        Get the current Kubernetes namespace.

        Returns
        -------
            Current namespace name, or 'layer-3-cloud' as default

        """
        # Check if running in a pod (K8s injects this file)
        namespace_file = Path("/var/run/secrets/kubernetes.io/serviceaccount/namespace")
        if namespace_file.exists():
            return namespace_file.read_text().strip()

        # Default to layer-3-cloud for kubectl-based access
        return "layer-3-cloud"

    def get_active_route(self) -> str:
        """
        Get the currently active KStack route.

        Returns
        -------
            Active route name (e.g., 'development', 'staging', 'production')

        Raises
        ------
            RuntimeError: If route cannot be determined

        """
        # Check environment variable first
        route = os.environ.get("KSTACK_ROUTE")
        if route:
            return route

        # Try to get from kubectl context (route is stored in ConfigMap)
        try:
            result = subprocess.run(
                [
                    "kubectl",
                    "get",
                    "configmap",
                    "kstack-route",
                    "-n",
                    "layer-3-cloud",
                    "-o",
                    "jsonpath={.data.active-route}",
                ],
                capture_output=True,
                text=True,
                check=True,
            )
            route = result.stdout.strip()
            if route:
                return route
        except (subprocess.CalledProcessError, FileNotFoundError):
            pass

        # Default to development for local development
        return "development"

    def get_redis_config(
        self,
        database: Literal["part-raw", "part-audit"] = "part-raw",
    ) -> RedisConfig:
        """
        Get Redis configuration for the active route.

        Args:
        ----
            database: Which database to connect to ('part-raw' or 'part-audit')

        Returns:
        -------
            RedisConfig with host, port, username, password

        Raises:
        ------
            ValueError: If configuration not found
            FileNotFoundError: If vault files not found

        """
        active_route = self.get_active_route()

        # Try to read from decrypted vault file first
        vault_file = self.vault_dir / "redis-cloud.yaml"
        if vault_file.exists():
            with open(vault_file) as f:
                vault_data = yaml.safe_load(f)

            if active_route in vault_data and database in vault_data[active_route]:
                config = vault_data[active_route][database]
                return RedisConfig(
                    host=config["host"],
                    port=int(config["port"]),
                    username=config.get("username", "default"),
                    password=config["password"],
                )

        # Try environment variables first (set by K8s deployment)
        env_prefix = "AUDIT_" if database == "part-audit" else ""
        host_env = os.environ.get(f"{env_prefix}REDIS_CLIENT_HOST")
        port_env = os.environ.get(f"{env_prefix}REDIS_CLIENT_PORT")
        password_env = os.environ.get(f"{env_prefix}REDIS_PASSWORD")
        username_env = os.environ.get(f"{env_prefix}REDIS_USERNAME", "default")

        if host_env and port_env and password_env:
            return RedisConfig(
                host=host_env,
                port=int(port_env),
                username=username_env,
                password=password_env,
            )

        # Fall back to reading from Kubernetes Secret (for deployed environments)
        try:
            secret_name = f"redis-credentials-{active_route}"
            prefix = "audit-" if database == "part-audit" else ""
            namespace = self.get_current_namespace()

            # Get values from K8s Secret
            host_result = subprocess.run(
                [
                    "kubectl",
                    "get",
                    "secret",
                    secret_name,
                    "-n",
                    namespace,
                    "-o",
                    f"jsonpath={{.data.{prefix}redis-host}}",
                ],
                capture_output=True,
                text=True,
                check=True,
            )

            port_result = subprocess.run(
                [
                    "kubectl",
                    "get",
                    "secret",
                    secret_name,
                    "-n",
                    namespace,
                    "-o",
                    f"jsonpath={{.data.{prefix}redis-port}}",
                ],
                capture_output=True,
                text=True,
                check=True,
            )

            username_result = subprocess.run(
                [
                    "kubectl",
                    "get",
                    "secret",
                    secret_name,
                    "-n",
                    namespace,
                    "-o",
                    f"jsonpath={{.data.{prefix}redis-username}}",
                ],
                capture_output=True,
                text=True,
                check=True,
            )

            password_result = subprocess.run(
                [
                    "kubectl",
                    "get",
                    "secret",
                    secret_name,
                    "-n",
                    namespace,
                    "-o",
                    f"jsonpath={{.data.{prefix}redis-password}}",
                ],
                capture_output=True,
                text=True,
                check=True,
            )

            # Decode base64 values
            import base64

            host = base64.b64decode(host_result.stdout.strip()).decode()
            port = int(base64.b64decode(port_result.stdout.strip()).decode())
            username = base64.b64decode(username_result.stdout.strip()).decode()
            password = base64.b64decode(password_result.stdout.strip()).decode()

            return RedisConfig(host=host, port=port, username=username, password=password)

        except (subprocess.CalledProcessError, FileNotFoundError):
            pass

        raise ServiceNotFoundError(
            f"Redis configuration not found for route '{active_route}' and database '{database}'. "
            f"Please ensure vault is configured or secrets are deployed.",
        )


def get_redis_config(
    config_map: "ConfigMap | None" = None,
    database: "KStackRedisDatabase | Literal['part-raw', 'part-audit'] | None" = None,
) -> RedisConfig:
    """
    Get Redis configuration for the specified layer and database.

    Args:
    ----
        config_map: ConfigMap instance specifying which layer to access Redis from.
                   If None, creates a default ConfigMap (backward compatibility).
        database: Redis database to connect to. Can be:
                 - KStackRedisDatabase enum (recommended)
                 - String literal "part-raw" or "part-audit" (deprecated)
                 If None, defaults to PART_RAW.

    Returns:
    -------
        RedisConfig with host, port, username, password

    Raises:
    ------
        LayerAccessError: If trying to access Redis from a layer that doesn't have it
        ServiceNotFoundError: If configuration not found

    Example (Recommended):
    ---------------------
        from kstack_lib.config import ConfigMap, get_redis_config
        from kstack_lib.types import KStackLayer, KStackRedisDatabase

        cfg = ConfigMap(layer=KStackLayer.LAYER_3_GLOBAL_INFRA)
        config = get_redis_config(cfg, KStackRedisDatabase.PART_RAW)

    Example (Deprecated but still supported):
    -----------------------------------------
        config = get_redis_config(database='part-raw')

    """
    # Import here to avoid circular imports
    from kstack_lib.config.configmap import ConfigMap
    from kstack_lib.types import KStackLayer

    # Handle backward compatibility - if no config_map provided, create default
    if config_map is None:
        # Default to Layer 3 for backward compatibility
        config_map = ConfigMap(layer=KStackLayer.LAYER_3_GLOBAL_INFRA)

    # Validate layer - Redis is only in Layer 3
    if config_map.layer != KStackLayer.LAYER_3_GLOBAL_INFRA:
        raise LayerAccessError(
            f"Redis databases are only available in {KStackLayer.LAYER_3_GLOBAL_INFRA.display_name}. "
            f"You are trying to access from {config_map.layer.display_name}."
        )

    # Handle database parameter - support both enum and string for backward compatibility
    if database is None:
        database_str = "part-raw"  # Default
    elif isinstance(database, str):
        database_str = database
    else:
        # It's a KStackRedisDatabase enum
        database_str = database.value

    discovery = RedisDiscovery()
    return discovery.get_redis_config(database=database_str)  # type: ignore[arg-type]
