"""
Protocol definitions for KStack.

These protocols define the contracts that adapters must implement.
Protocols enable dependency injection and context-specific implementations.

All protocols follow PEP 544 (Structural Subtyping / Protocol).
"""

from pathlib import Path
from typing import Any, Protocol, runtime_checkable


@runtime_checkable
class EnvironmentDetector(Protocol):
    """
    Protocol for detecting the active environment and configuration paths.

    Implementations:
    - cluster/config/environment.py - Reads from K8s namespace
    - local/config/environment.py - Reads from .kstack.yaml
    """

    def get_environment(self) -> str:
        """
        Get the active environment name.

        Returns
        -------
            Environment name (e.g., "dev", "testing", "staging", "production")

        Raises
        ------
            RuntimeError: If environment cannot be determined

        """
        ...

    def get_config_root(self) -> Path | None:
        """
        Get the root path for configuration files.

        Returns:
        -------
            Path to config root (environments/, providers/) or None if in-cluster

        Note:
        ----
            Returns None in-cluster (configs come from K8s ConfigMaps)
            Returns Path outside cluster (configs come from files)

        """
        ...

    def get_vault_root(self) -> Path | None:
        """
        Get the root path for vault files.

        Returns:
        -------
            Path to vault root or None if in-cluster

        Note:
        ----
            Returns None in-cluster (no vault in production!)
            Returns Path outside cluster (vault/ directory)

        """
        ...


@runtime_checkable
class SecretsProvider(Protocol):
    """
    Protocol for accessing secrets and credentials.

    Implementations:
    - cluster/security/secrets.py - Reads from K8s Secrets
    - local/security/credentials.py - Reads from partsecrets vault
    """

    def get_credentials(self, service: str, layer: str, environment: str) -> dict:
        """
        Get credentials for a service.

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
            >>> creds = provider.get_credentials("s3", "layer3", "dev")
            >>> print(creds["aws_access_key_id"])

        """
        ...


@runtime_checkable
class ConfigProvider(Protocol):
    """
    Protocol for loading configuration data.

    Implementations:
    - cluster/config/loader.py - Reads from K8s ConfigMaps
    - local/config/loader.py - Reads from YAML files
    """

    def load_config(self, config_type: str, name: str) -> dict:
        """
        Load configuration by type and name.

        Args:
        ----
            config_type: Type of config ("environment", "provider", etc.)
            name: Config name (e.g., "dev", "localstack")

        Returns:
        -------
            Configuration dictionary

        Raises:
        ------
            KStackConfigurationError: If config not found or invalid

        Example:
        -------
            >>> config = provider.load_config("provider", "localstack")
            >>> print(config["endpoint_url"])

        """
        ...


@runtime_checkable
class VaultManager(Protocol):
    """
    Protocol for vault encryption/decryption operations.

    Implementation:
    - local/security/vault.py - KStackVault (partsecrets)

    Note:
    ----
        This protocol is LOCAL-ONLY. There is no cluster implementation
        because vaults don't exist in production.

    """

    def is_encrypted(self) -> bool:
        """Check if vault is currently encrypted."""
        ...

    def decrypt(self, team: str = "dev") -> bool:
        """
        Decrypt vault files.

        Args:
        ----
            team: Team name for partsecrets

        Returns:
        -------
            True if successful, False otherwise

        """
        ...

    def encrypt(self, team: str = "dev") -> bool:
        """
        Encrypt vault files.

        Args:
        ----
            team: Team name for partsecrets

        Returns:
        -------
            True if successful, False otherwise

        """
        ...

    def get_file(self, layer: str, filename: str) -> Path:
        """
        Get path to a vault file.

        Args:
        ----
            layer: Layer identifier (e.g., "layer3")
            filename: Filename (decrypted name)

        Returns:
        -------
            Path to the file

        """
        ...


@runtime_checkable
class CloudSessionFactory(Protocol):
    """
    Protocol for creating cloud provider sessions (boto3, etc.).

    Implementations can provide sync and/or async sessions.

    Note:
    ----
        Sessions are auto-configured from credentials (vault or K8s secrets)

    """

    def create_session(self, service: str, layer: str, environment: str) -> Any:
        """
        Create a synchronous cloud session (e.g., boto3.Session).

        Args:
        ----
            service: Service name (e.g., "s3", "dynamodb")
            layer: Layer identifier (e.g., "layer3")
            environment: Environment name (e.g., "dev", "production")

        Returns:
        -------
            Cloud provider session object

        Example:
        -------
            >>> factory = get_cloud_session_factory()
            >>> session = factory.create_session("s3", "layer3", "dev")
            >>> s3_client = session.client("s3")

        """
        ...

    def create_async_session(self, service: str, layer: str, environment: str) -> Any:
        """
        Create an asynchronous cloud session (e.g., aioboto3.Session).

        Args:
        ----
            service: Service name (e.g., "s3", "dynamodb")
            layer: Layer identifier (e.g., "layer3")
            environment: Environment name (e.g., "dev", "production")

        Returns:
        -------
            Async cloud provider session object

        Example:
        -------
            >>> factory = get_cloud_session_factory()
            >>> session = factory.create_async_session("s3", "layer3", "dev")
            >>> async with session.client("s3") as s3:
            >>>     await s3.list_buckets()

        """
        ...
