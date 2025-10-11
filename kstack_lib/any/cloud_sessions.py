"""
Cloud session factory for boto3/aioboto3 (context-agnostic).

Creates cloud provider sessions auto-configured from credentials.
Works in both cluster and local contexts via DI.
"""

from typing import Any

from partsnap_logger.logging import psnap_get_logger

from kstack_lib.any.exceptions import KStackConfigurationError

LOGGER = psnap_get_logger("kstack_lib.any.cloud_sessions")


class Boto3SessionFactory:
    """
    Factory for creating boto3/aioboto3 sessions from credentials.

    Auto-configured from credentials provider (vault or K8s secrets).

    Example:
    -------
        ```python
        from kstack_lib.any import get_cloud_session_factory

        factory = get_cloud_session_factory()

        # Sync session
        session = factory.create_session("s3", "layer3", "dev")
        s3_client = session.client("s3")

        # Async session
        async_session = factory.create_async_session("s3", "layer3", "dev")
        async with async_session.client("s3") as s3:
            await s3.list_buckets()
        ```

    """

    def __init__(self, secrets_provider):
        """
        Initialize session factory.

        Args:
        ----
            secrets_provider: SecretsProvider instance (injected by container)

        """
        self._secrets = secrets_provider
        LOGGER.debug(f"Initialized Boto3SessionFactory with {secrets_provider}")

    def create_session(self, service: str, layer: str, environment: str) -> Any:
        """
        Create a boto3.Session configured from credentials.

        Args:
        ----
            service: Service name (e.g., "s3", "dynamodb")
            layer: Layer identifier (e.g., "layer3")
            environment: Environment name (e.g., "dev", "production")

        Returns:
        -------
            Configured boto3.Session

        Raises:
        ------
            KStackConfigurationError: If credentials missing or boto3 not available

        """
        try:
            import boto3
        except ImportError:
            raise KStackConfigurationError("boto3 not installed. Install with: uv add boto3")

        # Get credentials from provider (vault or K8s secrets)
        creds = self._secrets.get_credentials(service, layer, environment)

        # Extract AWS credentials
        aws_access_key_id = creds.get("aws_access_key_id")
        aws_secret_access_key = creds.get("aws_secret_access_key")
        region_name = creds.get("aws_region", "us-east-1")
        endpoint_url = creds.get("endpoint_url")  # For LocalStack

        if not aws_access_key_id or not aws_secret_access_key:
            raise KStackConfigurationError(
                f"Missing AWS credentials for {service} in {layer}/{environment}\n"
                f"Required: aws_access_key_id, aws_secret_access_key"
            )

        # Create session
        session = boto3.Session(
            aws_access_key_id=aws_access_key_id,
            aws_secret_access_key=aws_secret_access_key,
            region_name=region_name,
        )

        LOGGER.debug(
            f"Created boto3 session for {service} in {layer}/{environment} "
            f"(region: {region_name}, endpoint: {endpoint_url or 'default'})"
        )

        return session

    def create_async_session(self, service: str, layer: str, environment: str) -> Any:
        """
        Create an aioboto3.Session configured from credentials.

        Args:
        ----
            service: Service name (e.g., "s3", "dynamodb")
            layer: Layer identifier (e.g., "layer3")
            environment: Environment name (e.g., "dev", "production")

        Returns:
        -------
            Configured aioboto3.Session

        Raises:
        ------
            KStackConfigurationError: If credentials missing or aioboto3 not available

        """
        try:
            import aioboto3
        except ImportError:
            raise KStackConfigurationError("aioboto3 not installed. Install with: uv add aioboto3")

        # Get credentials from provider (vault or K8s secrets)
        creds = self._secrets.get_credentials(service, layer, environment)

        # Extract AWS credentials
        aws_access_key_id = creds.get("aws_access_key_id")
        aws_secret_access_key = creds.get("aws_secret_access_key")
        region_name = creds.get("aws_region", "us-east-1")
        endpoint_url = creds.get("endpoint_url")  # For LocalStack

        if not aws_access_key_id or not aws_secret_access_key:
            raise KStackConfigurationError(
                f"Missing AWS credentials for {service} in {layer}/{environment}\n"
                f"Required: aws_access_key_id, aws_secret_access_key"
            )

        # Create async session
        session = aioboto3.Session(
            aws_access_key_id=aws_access_key_id,
            aws_secret_access_key=aws_secret_access_key,
            region_name=region_name,
        )

        LOGGER.debug(
            f"Created aioboto3 session for {service} in {layer}/{environment} "
            f"(region: {region_name}, endpoint: {endpoint_url or 'default'})"
        )

        return session

    def __repr__(self) -> str:
        """String representation."""
        return f"Boto3SessionFactory(secrets={self._secrets})"
