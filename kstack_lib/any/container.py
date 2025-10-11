"""
Dependency injection container for KStack.

This container auto-wires adapters based on context (cluster vs local).
Uses dependency-injector for clean DI with singletons.
"""

from dependency_injector import containers, providers

from kstack_lib.any.context import is_in_cluster
from kstack_lib.any.protocols import (
    CloudSessionFactory,
    EnvironmentDetector,
    SecretsProvider,
    VaultManager,
)


def _context_selector() -> str:
    """Return 'cluster' or 'local' based on context for Selector provider."""
    return "cluster" if is_in_cluster() else "local"


class KStackIoCContainer(containers.DeclarativeContainer):
    """
    Inversion of Control (IoC) container for KStack.

    Auto-wires the correct adapters based on whether we're in-cluster or local.
    Uses dependency-injector for clean DI with singletons.

    Example:
    -------
        ```python
        from kstack_lib.any.container import KStackIoCContainer

        # Container auto-detects context and wires adapters
        container = KStackIoCContainer()

        # Get environment detector (singleton)
        env_detector = container.environment_detector()
        env = env_detector.get_environment()

        # Get secrets provider (auto-wired based on context)
        secrets = container.secrets_provider()
        creds = secrets.get_credentials("s3", "layer3", env)
        ```

    """

    # Singleton: Environment detector (created once, reused)
    # Auto-selects ClusterEnvironmentDetector or LocalEnvironmentDetector
    environment_detector = providers.Singleton(
        providers.Selector(
            _context_selector,
            cluster=providers.Factory(
                lambda: __import__(
                    "kstack_lib.cluster.config.environment",
                    fromlist=["ClusterEnvironmentDetector"],
                ).ClusterEnvironmentDetector()
            ),
            local=providers.Factory(
                lambda: __import__(
                    "kstack_lib.local.config.environment",
                    fromlist=["LocalEnvironmentDetector"],
                ).LocalEnvironmentDetector()
            ),
        )
    )

    # Singleton: Vault manager (LOCAL-ONLY, will error if accessed in-cluster)
    vault_manager = providers.Singleton(
        providers.Callable(
            lambda env_detector: __import__(
                "kstack_lib.local.security.vault",
                fromlist=["KStackVault"],
            ).KStackVault(environment=env_detector.get_environment()),
            env_detector=environment_detector,
        )
    )

    # Singleton: Secrets provider
    # Auto-selects ClusterSecretsProvider or LocalCredentialsProvider
    secrets_provider = providers.Singleton(
        providers.Selector(
            _context_selector,
            cluster=providers.Factory(
                lambda: __import__(
                    "kstack_lib.cluster.security.secrets",
                    fromlist=["ClusterSecretsProvider"],
                ).ClusterSecretsProvider()
            ),
            local=providers.Callable(
                lambda vault, env_detector: __import__(
                    "kstack_lib.local.security.credentials",
                    fromlist=["LocalCredentialsProvider"],
                ).LocalCredentialsProvider(vault=vault, environment=env_detector.get_environment()),
                vault=vault_manager,
                env_detector=environment_detector,
            ),
        )
    )

    # Singleton: Cloud session factory (boto3/aioboto3)
    # Automatically configured from secrets provider
    cloud_session_factory = providers.Singleton(
        providers.Callable(
            lambda secrets: __import__(
                "kstack_lib.any.cloud_sessions",
                fromlist=["Boto3SessionFactory"],
            ).Boto3SessionFactory(secrets_provider=secrets),
            secrets=secrets_provider,
        )
    )


# Global singleton container instance
container = KStackIoCContainer()


def get_environment_detector() -> EnvironmentDetector:
    """
    Get environment detector (singleton).

    Returns:
    -------
        EnvironmentDetector implementation (cluster or local)

    Example:
    -------
        ```python
        from kstack_lib.any.container import get_environment_detector

        detector = get_environment_detector()
        env = detector.get_environment()
        ```

    """
    return container.environment_detector()


def get_secrets_provider() -> SecretsProvider:
    """
    Get secrets provider (singleton).

    Returns:
    -------
        SecretsProvider implementation (cluster or local)

    Example:
    -------
        ```python
        from kstack_lib.any.container import get_secrets_provider

        secrets = get_secrets_provider()
        creds = secrets.get_credentials("s3", "layer3", "dev")
        ```

    """
    return container.secrets_provider()


def get_vault_manager() -> VaultManager:
    """
    Get vault manager (singleton, LOCAL-ONLY).

    Returns:
    -------
        KStackVault instance

    Raises:
    ------
        KStackEnvironmentError: If called in-cluster

    Example:
    -------
        ```python
        from kstack_lib.any.container import get_vault_manager

        vault = get_vault_manager()  # Raises in-cluster
        vault.decrypt()
        ```

    """
    return container.vault_manager()


def get_cloud_session_factory() -> CloudSessionFactory:
    """
    Get cloud session factory (singleton).

    Returns:
    -------
        Boto3SessionFactory instance

    Example:
    -------
        ```python
        from kstack_lib.any.container import get_cloud_session_factory

        factory = get_cloud_session_factory()
        session = factory.create_session("s3", "layer3", "dev")
        s3_client = session.client("s3")
        ```

    """
    return container.cloud_session_factory()
