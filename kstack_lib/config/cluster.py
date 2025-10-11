"""
Cluster configuration and environment detection.

Provides KStackClusterConfig for detecting the active environment,
whether running in-cluster (Kubernetes) or outside (dev machine).
"""

from pathlib import Path

import yaml
from partsnap_logger.logging import psnap_get_logger

from kstack_lib.types import KStackEnvironment

LOGGER = psnap_get_logger("kstack_lib.config.cluster")


class KStackClusterConfig:
    """
    Manages cluster configuration and environment detection.

    Automatically detects whether running inside Kubernetes or on a dev machine,
    and determines the active environment accordingly.

    In-cluster detection:
        - Reads environment from Kubernetes namespace or configmap
        - Uses K8s service account tokens and namespace files

    Outside cluster detection:
        - Searches for .kstack.yaml config file
        - Walks up directory tree to find partsnap-kstack repo
        - Does NOT rely on KSTACK_ENVIRONMENT (dangerous in production)

    Example:
    -------
        ```python
        # Get active environment
        cluster_config = KStackClusterConfig()
        env = cluster_config.environment
        print(f"Running in: {env}")  # "dev", "testing", "staging", "production"

        # Check if in cluster
        if cluster_config.is_in_cluster:
            print("Running inside Kubernetes")
        else:
            print("Running on dev machine")
        ```

    """

    def __init__(self, config_root: Path | None = None):
        """
        Initialize cluster configuration.

        Args:
        ----
            config_root: Optional path to kstack config root (for testing)
                        If not provided, will auto-detect

        """
        self._config_root = config_root
        self.is_in_cluster = self._detect_in_cluster()
        self.environment = self._detect_environment()

        LOGGER.info(
            f"Cluster config initialized: environment='{self.environment}', " f"in_cluster={self.is_in_cluster}"
        )

    def _detect_in_cluster(self) -> bool:
        """
        Detect if running inside Kubernetes cluster.

        Returns
        -------
            True if running inside K8s cluster, False otherwise

        """
        # Check for Kubernetes service account token
        token_file = Path("/var/run/secrets/kubernetes.io/serviceaccount/token")
        namespace_file = Path("/var/run/secrets/kubernetes.io/serviceaccount/namespace")

        in_cluster = token_file.exists() and namespace_file.exists()

        if in_cluster:
            LOGGER.debug("Detected in-cluster execution (Kubernetes)")
        else:
            LOGGER.debug("Detected out-of-cluster execution (dev machine)")

        return in_cluster

    def _detect_environment(self) -> str:
        """
        Detect the active environment.

        Returns
        -------
            Environment name (e.g., "dev", "testing", "staging", "production")

        """
        if self.is_in_cluster:
            return self._detect_from_kubernetes()
        else:
            return self._detect_from_kstack_yaml()

    def _detect_from_kubernetes(self) -> str:
        """
        Detect environment from Kubernetes namespace.

        The namespace format is expected to be: layer-{N}-{environment}-{scope}
        For example: layer-3-dev-global-infra or layer-0-production-apps

        Returns
        -------
            Environment name extracted from namespace

        Raises
        ------
            RuntimeError: If namespace cannot be read or doesn't match expected format

        """
        namespace_file = Path("/var/run/secrets/kubernetes.io/serviceaccount/namespace")

        try:
            namespace = namespace_file.read_text().strip()
            LOGGER.debug(f"Running in namespace: {namespace}")
        except Exception as e:
            LOGGER.error(f"Failed to read namespace from {namespace_file}: {e}")
            raise RuntimeError(
                f"Cannot read Kubernetes namespace from {namespace_file}. "
                f"This should never fail in-cluster. Error: {e}"
            ) from e

        # Parse namespace to extract environment
        # Expected format: layer-{N}-{environment}-{scope}
        parts = namespace.split("-")

        if len(parts) >= 3 and parts[0] == "layer":
            # parts[1] is layer number, parts[2] is environment
            env = parts[2]
            LOGGER.info(f"Detected environment from namespace: {env}")
            return env

        # Namespace doesn't match expected format - this is a critical error
        LOGGER.error(f"Namespace '{namespace}' doesn't match expected format 'layer-{{N}}-{{environment}}-{{scope}}'")
        raise RuntimeError(
            f"Invalid namespace format: '{namespace}'\n"
            f"Expected format: layer-{{N}}-{{environment}}-{{scope}}\n"
            f"Examples: layer-3-dev-global-infra, layer-0-production-apps\n"
            f"\n"
            f"Running in production with wrong environment detection is DANGEROUS.\n"
            f"Please check your namespace configuration."
        )

    def _detect_from_kstack_yaml(self) -> str:
        """
        Detect environment from .kstack.yaml config file.

        Searches for .kstack.yaml by walking up the directory tree.
        Does NOT use KSTACK_ENVIRONMENT environment variable (dangerous).

        Returns
        -------
            Environment name from .kstack.yaml or default "dev"

        Raises
        ------
            RuntimeError: If .kstack.yaml exists but cannot be read or parsed

        """
        config_file = self._find_kstack_yaml()

        if config_file is None:
            LOGGER.warning("Could not find .kstack.yaml, defaulting to 'dev'")
            return "dev"

        # If we found a config file, we MUST be able to read it
        try:
            with open(config_file) as f:
                config = yaml.safe_load(f) or {}
        except Exception as e:
            LOGGER.error(f"Failed to read {config_file}: {e}")
            raise RuntimeError(
                f"Found .kstack.yaml at {config_file} but cannot read it.\n"
                f"Error: {e}\n"
                f"\n"
                f"This is a critical error - please check file permissions and YAML syntax."
            ) from e

        env = config.get("environment", "dev")
        LOGGER.info(f"Loaded environment from {config_file}: {env}")
        return env

    def _find_kstack_yaml(self) -> Path | None:
        """
        Find .kstack.yaml by searching up directory tree.

        Returns
        -------
            Path to .kstack.yaml or None if not found

        """
        if self._config_root:
            # Explicit config root provided (for testing)
            config_file = self._config_root / ".kstack.yaml"
            if config_file.exists():
                return config_file
            return None

        # Start from current working directory
        current = Path.cwd()

        # Search up to 10 levels (generous limit)
        for _ in range(10):
            config_file = current / ".kstack.yaml"

            if config_file.exists():
                LOGGER.debug(f"Found .kstack.yaml at: {config_file}")
                return config_file

            # Move up one directory
            if current.parent == current:
                # Reached filesystem root
                break
            current = current.parent

        LOGGER.warning("Could not find .kstack.yaml in directory tree")
        return None

    def get_environment_enum(self) -> KStackEnvironment:
        """
        Get the environment as a KStackEnvironment enum.

        Returns
        -------
            KStackEnvironment enum value

        Raises
        ------
            ValueError: If environment is not valid

        """
        return KStackEnvironment.from_string(self.environment)

    def __repr__(self) -> str:
        """String representation."""
        return f"KStackClusterConfig(environment='{self.environment}', " f"in_cluster={self.is_in_cluster})"


def get_active_environment() -> str:
    """
    Get the currently active environment.

    This is a convenience function that creates a KStackClusterConfig
    and returns the detected environment.

    Returns:
    -------
        Active environment name (e.g., "dev", "testing", "staging", "production")

    Example:
    -------
        ```python
        env = get_active_environment()
        print(f"Active environment: {env}")
        ```

    """
    cluster_config = KStackClusterConfig()
    return cluster_config.environment
