"""
LocalStack configuration discovery and management.

This module provides configuration discovery for LocalStack instances,
similar to RedisDiscovery but for AWS service emulation.
"""

import os
import subprocess
from pathlib import Path
from typing import Any

import yaml


class LocalStackDiscovery:
    """
    Discover and manage LocalStack configuration based on active route.

    LocalStack instances are deployed per-route (development, testing, scratch, etc.)
    and provide AWS service emulation (S3, SQS, SNS, RDS, Lambda, etc.).

    Example:
    -------
        discovery = LocalStackDiscovery()
        route = discovery.get_active_route()  # → "development"
        config = discovery.get_localstack_config()  # → {"endpoint_url": "http://...", ...}

    """

    def __init__(self, vault_dir: Path | None = None):
        """
        Initialize LocalStack discovery.

        Args:
        ----
            vault_dir: Path to vault directory (defaults to ./vault/dev)

        """
        if vault_dir is None:
            vault_dir = Path.cwd() / "vault" / "dev"
        self.vault_dir = Path(vault_dir)

    def get_active_route(self) -> str:
        """
        Determine which route/environment is currently active.

        Priority:
        1. KSTACK_ROUTE environment variable (for local development)
        2. kstack-route ConfigMap in Kubernetes (for K8s deployments)
        3. Default to "development"

        Returns
        -------
            Active route name (e.g., "development", "testing", "scratch")

        """
        # Priority 1: Environment variable (local dev override)
        route = os.environ.get("KSTACK_ROUTE")
        if route:
            return route

        # Priority 2: Kubernetes ConfigMap (inside K8s)
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
                check=False,
            )
            if result.returncode == 0 and result.stdout.strip():
                return result.stdout.strip()
        except FileNotFoundError:
            pass

        # Priority 3: Default
        return "development"

    def get_localstack_config(self, route: str | None = None) -> dict[str, Any]:
        """
        Get LocalStack configuration for the active route.

        Args:
        ----
            route: Optional route override (uses active route if not specified)

        Returns:
        -------
            Dictionary with LocalStack configuration:
            - endpoint_url: LocalStack endpoint (e.g., "http://localstack-development.layer-3-cloud:4566")
            - aws_access_key_id: AWS access key (usually "test")
            - aws_secret_access_key: AWS secret key (usually "test")
            - region_name: AWS region (usually "us-east-1")

        Raises:
        ------
            ValueError: If configuration cannot be found

        """
        if route is None:
            route = self.get_active_route()

        # Try reading from vault file (local development)
        vault_file = self.vault_dir / "localstack-cloud.yaml"
        if vault_file.exists():
            try:
                with vault_file.open("r") as f:
                    vault_data = yaml.safe_load(f)
                    if route in vault_data:
                        return vault_data[route]
            except Exception:
                pass

        # Try reading from Kubernetes Secret (inside K8s)
        try:
            secret_name = f"localstack-credentials-{route}"
            result = subprocess.run(
                [
                    "kubectl",
                    "get",
                    "secret",
                    secret_name,
                    "-n",
                    "layer-3-cloud",
                    "-o",
                    "jsonpath={.data}",
                ],
                capture_output=True,
                text=True,
                check=False,
            )
            if result.returncode == 0:
                import base64
                import json

                secret_data = json.loads(result.stdout)
                return {
                    "endpoint_url": base64.b64decode(secret_data["endpoint-url"]).decode(),
                    "aws_access_key_id": base64.b64decode(secret_data.get("aws-access-key-id", b"test")).decode(),
                    "aws_secret_access_key": base64.b64decode(
                        secret_data.get("aws-secret-access-key", b"test"),
                    ).decode(),
                    "region_name": base64.b64decode(secret_data.get("region-name", b"us-east-1")).decode(),
                }
        except Exception:
            pass

        # Fallback: Construct default configuration based on route
        return {
            "endpoint_url": f"http://localstack-{route}.layer-3-cloud:4566",
            "aws_access_key_id": "test",
            "aws_secret_access_key": "test",
            "region_name": "us-east-1",
        }


def get_localstack_config(route: str | None = None) -> dict[str, Any]:
    """
    Get LocalStack configuration for the active route.

    Convenience function that creates a LocalStackDiscovery instance and
    retrieves configuration.

    Args:
    ----
        route: Optional route override (uses active route if not specified)

    Returns:
    -------
        Dictionary with LocalStack configuration

    Example:
    -------
        config = get_localstack_config()
        # → {"endpoint_url": "http://localstack-development...", ...}

        config = get_localstack_config(route="testing")
        # → {"endpoint_url": "http://localstack-testing...", ...}

    """
    discovery = LocalStackDiscovery()
    return discovery.get_localstack_config(route=route)
