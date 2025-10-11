"""
Cluster secrets provider using Kubernetes Secret Manager (CLUSTER-ONLY).

This adapter implements the SecretsProvider protocol using K8s secrets.
It will raise KStackEnvironmentError if imported outside the cluster.
"""

import base64
import subprocess

from partsnap_logger.logging import psnap_get_logger

from kstack_lib.any.exceptions import KStackConfigurationError, KStackServiceNotFoundError
from kstack_lib.any.utils import run_command
from kstack_lib.cluster._guards import _enforce_cluster  # noqa: F401 - Import guard

LOGGER = psnap_get_logger("kstack_lib.cluster.security.secrets")


class ClusterSecretsProvider:
    """
    Provides credentials from Kubernetes Secret Manager.

    Implements the SecretsProvider protocol for in-cluster usage.

    Example:
    -------
        ```python
        # In-cluster only
        provider = ClusterSecretsProvider()
        creds = provider.get_credentials("s3", "layer3", "production")
        print(creds["aws_access_key_id"])
        ```

    """

    def __init__(self, namespace: str | None = None):
        """
        Initialize cluster secrets provider.

        Args:
        ----
            namespace: Optional namespace (defaults to current namespace from env)

        """
        self._namespace = namespace or self._get_current_namespace()
        LOGGER.debug(f"Initialized cluster secrets provider in namespace: {self._namespace}")

    def _get_current_namespace(self) -> str:
        """
        Get current namespace from service account.

        Returns
        -------
            Current namespace

        Raises
        ------
            KStackConfigurationError: If namespace cannot be determined

        """
        namespace_file = "/var/run/secrets/kubernetes.io/serviceaccount/namespace"
        try:
            with open(namespace_file) as f:
                namespace = f.read().strip()
                LOGGER.debug(f"Detected namespace from service account: {namespace}")
                return namespace
        except FileNotFoundError:
            raise KStackConfigurationError(
                f"Cannot read namespace from {namespace_file}\n"
                "This should not happen in a properly configured K8s pod."
            )

    def get_credentials(self, service: str, layer: str, environment: str) -> dict:
        """
        Get credentials for a service from K8s secrets.

        Args:
        ----
            service: Service name (e.g., "s3", "redis", "postgres")
            layer: Layer identifier (e.g., "layer3", "layer1")
            environment: Environment name (e.g., "dev", "production")

        Returns:
        -------
            Dictionary containing credentials (keys depend on service)

        Raises:
        ------
            KStackServiceNotFoundError: If secret not found
            KStackConfigurationError: If secret malformed

        Example:
        -------
            >>> provider = ClusterSecretsProvider()
            >>> creds = provider.get_credentials("s3", "layer3", "production")
            >>> print(creds["aws_access_key_id"])

        """
        # K8s secret naming: {layer}-{service}-credentials
        secret_name = f"{layer}-{service}-credentials"

        LOGGER.debug(
            f"Fetching K8s secret: {secret_name} " f"(namespace: {self._namespace}, environment: {environment})"
        )

        # Get secret from K8s
        try:
            result = run_command(
                [
                    "kubectl",
                    "get",
                    "secret",
                    secret_name,
                    "-n",
                    self._namespace,
                    "-o",
                    "json",
                ],
                check=True,
            )
        except subprocess.CalledProcessError as e:
            if "NotFound" in str(e.stderr):
                raise KStackServiceNotFoundError(
                    f"K8s secret not found: {secret_name} in namespace {self._namespace}\n"
                    f"Service: {service}, Layer: {layer}, Environment: {environment}"
                )
            raise KStackConfigurationError(f"Failed to fetch K8s secret: {secret_name}\n" f"Error: {e.stderr}") from e

        # Parse secret data
        import json

        try:
            secret_data = json.loads(result.stdout)
            data = secret_data.get("data", {})
        except json.JSONDecodeError as e:
            raise KStackConfigurationError(f"Failed to parse K8s secret JSON: {secret_name}\n" f"Error: {e}") from e

        # Decode base64 values and build credentials dict
        credentials = {}
        for key, encoded_value in data.items():
            try:
                decoded_value = base64.b64decode(encoded_value).decode("utf-8")
                credentials[key] = decoded_value
            except Exception as e:
                LOGGER.warning(f"Failed to decode secret key '{key}': {e}")
                continue

        if not credentials:
            raise KStackConfigurationError(
                f"K8s secret {secret_name} is empty or malformed\n" f"Expected base64-encoded credential keys"
            )

        LOGGER.debug(
            f"Loaded credentials for {service} from K8s secret: {secret_name} "
            f"(keys: {', '.join(credentials.keys())})"
        )

        return credentials

    def __repr__(self) -> str:
        """String representation."""
        return f"ClusterSecretsProvider(namespace='{self._namespace}')"
