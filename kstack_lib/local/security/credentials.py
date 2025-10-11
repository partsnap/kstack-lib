"""
Local credentials provider using partsecrets vault (LOCAL-ONLY).

This adapter implements the SecretsProvider protocol using the local vault.
It will raise KStackEnvironmentError if imported in-cluster.
"""

import yaml
from partsnap_logger.logging import psnap_get_logger

from kstack_lib.any.exceptions import KStackConfigurationError, KStackServiceNotFoundError
from kstack_lib.local._guards import _enforce_local  # noqa: F401 - Import guard
from kstack_lib.local.security.vault import KStackVault

LOGGER = psnap_get_logger("kstack_lib.local.security.credentials")


class LocalCredentialsProvider:
    """
    Provides credentials from local partsecrets vault.

    Implements the SecretsProvider protocol for local development.

    Example:
    -------
        ```python
        provider = LocalCredentialsProvider(environment="dev")
        creds = provider.get_credentials("s3", "layer3", "dev")
        print(creds["aws_access_key_id"])
        ```

    """

    def __init__(self, vault: KStackVault | None = None, environment: str | None = None):
        """
        Initialize credentials provider.

        Args:
        ----
            vault: Optional KStackVault instance (will create if not provided)
            environment: Environment name (required if vault not provided)

        """
        if vault is None and environment is None:
            raise ValueError("Either vault or environment must be provided")

        self._vault = vault or KStackVault(environment=environment)  # type: ignore
        LOGGER.debug(f"Initialized local credentials provider: {self._vault}")

    def get_credentials(self, service: str, layer: str, environment: str) -> dict:
        """
        Get credentials for a service from vault.

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
            KStackServiceNotFoundError: If credentials not found
            KStackConfigurationError: If credentials malformed

        Example:
        -------
            >>> provider = LocalCredentialsProvider(environment="dev")
            >>> creds = provider.get_credentials("s3", "layer3", "dev")
            >>> print(creds["aws_access_key_id"])

        """
        # Ensure vault environment matches requested environment
        if self._vault.environment != environment:
            raise KStackConfigurationError(
                f"Vault environment mismatch: vault is '{self._vault.environment}', " f"requested '{environment}'"
            )

        # Ensure vault is decrypted
        if self._vault.is_encrypted():
            LOGGER.info(f"Auto-decrypting vault for credentials access: {self._vault.path}")
            if not self._vault.decrypt():
                raise KStackConfigurationError(
                    f"Failed to decrypt vault: {self._vault.path}\n" "Cannot access credentials from encrypted vault."
                )

        # Look for credentials file
        # Pattern: vault/{environment}/{layer}/cloud-credentials.yaml
        creds_file = self._vault.get_file(layer, "cloud-credentials.yaml")

        if not creds_file.exists():
            raise KStackServiceNotFoundError(
                f"Credentials file not found: {creds_file}\n"
                f"Expected file: vault/{environment}/{layer}/cloud-credentials.yaml"
            )

        # Load and parse credentials
        try:
            with open(creds_file) as f:
                all_creds = yaml.safe_load(f)
        except Exception as e:
            raise KStackConfigurationError(f"Failed to parse credentials file: {creds_file}\n" f"Error: {e}") from e

        # Extract service-specific credentials
        if service not in all_creds:
            available = ", ".join(all_creds.keys())
            raise KStackServiceNotFoundError(
                f"Service '{service}' not found in credentials file: {creds_file}\n" f"Available services: {available}"
            )

        service_creds = all_creds[service]
        LOGGER.debug(f"Loaded credentials for {service} from {creds_file}")

        return service_creds

    def __repr__(self) -> str:
        """String representation."""
        return f"LocalCredentialsProvider(vault={self._vault})"
