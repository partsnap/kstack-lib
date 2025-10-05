"""
Redis configuration discovery for KStack.

Automatically discovers Redis endpoints based on the active route.
Applications use this to connect to the correct Redis instance without hardcoding credentials.

Example:
    from kstack_lib.config import get_redis_config

    # Automatically discovers based on active route
    config = get_redis_config(database='part-raw')
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
from typing import Literal, TypedDict

import yaml


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

        Returns:
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

        Returns:
            Active route name (e.g., 'development', 'staging', 'production')

        Raises:
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
            database: Which database to connect to ('part-raw' or 'part-audit')

        Returns:
            RedisConfig with host, port, username, password

        Raises:
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

        raise ValueError(
            f"Redis configuration not found for route '{active_route}' and database '{database}'. "
            f"Please ensure vault is configured or secrets are deployed.",
        )


def get_redis_config(
    database: Literal["part-raw", "part-audit"] = "part-raw",
) -> RedisConfig:
    """
    Get Redis configuration for the active route.

    Convenience function for getting Redis config without instantiating RedisDiscovery.

    Args:
        database: Which database to connect to ('part-raw' or 'part-audit')

    Returns:
        RedisConfig with host, port, username, password

    Example:
        config = get_redis_config(database='part-raw')
        redis_client = Redis(**config)

    """
    discovery = RedisDiscovery()
    return discovery.get_redis_config(database=database)
