"""
Cluster environment detection using Kubernetes namespace (CLUSTER-ONLY).

This adapter implements the EnvironmentDetector protocol for in-cluster usage.
It will raise KStackEnvironmentError if imported outside the cluster.
"""

from pathlib import Path

from partsnap_logger.logging import psnap_get_logger

from kstack_lib.any.exceptions import KStackConfigurationError
from kstack_lib.cluster._guards import _enforce_cluster  # noqa: F401 - Import guard

LOGGER = psnap_get_logger("kstack_lib.cluster.config.environment")


class ClusterEnvironmentDetector:
    """
    Detects environment from Kubernetes namespace.

    Implements the EnvironmentDetector protocol for in-cluster usage.

    Namespace format: layer-{layer_num}-{environment}
    Example: layer-3-production → environment = "production"

    Example:
    -------
        ```python
        # In-cluster only
        detector = ClusterEnvironmentDetector()
        env = detector.get_environment()  # "production"
        config_root = detector.get_config_root()  # None (uses ConfigMaps)
        vault_root = detector.get_vault_root()  # None (no vault in cluster!)
        ```

    """

    def __init__(self, namespace: str | None = None):
        """
        Initialize cluster environment detector.

        Args:
        ----
            namespace: Optional namespace (defaults to current namespace from service account)

        """
        self._namespace = namespace or self._get_current_namespace()
        LOGGER.debug(f"Initialized cluster environment detector: {self._namespace}")

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
        namespace_file = Path("/var/run/secrets/kubernetes.io/serviceaccount/namespace")
        if not namespace_file.exists():
            raise KStackConfigurationError(
                f"Cannot read namespace from {namespace_file}\n"
                "This should not happen in a properly configured K8s pod."
            )

        namespace = namespace_file.read_text().strip()
        LOGGER.debug(f"Detected namespace from service account: {namespace}")
        return namespace

    def get_environment(self) -> str:
        """
        Get environment from Kubernetes namespace.

        Namespace format: layer-{layer_num}-{environment}

        Examples
        --------
            - layer-3-production → "production"
            - layer-3-global-infra → "global-infra"
            - layer-2-staging → "staging"

        Returns
        -------
            Environment name (e.g., "production", "staging", "dev")

        Raises
        ------
            KStackConfigurationError: If namespace format is invalid

        """
        parts = self._namespace.split("-")

        # Validate format: layer-{num}-{environment}
        if len(parts) < 3:
            raise KStackConfigurationError(
                f"Invalid namespace format: '{self._namespace}'\n"
                "Expected format: layer-{layer_num}-{environment}\n"
                "Examples: layer-3-production, layer-2-staging\n\n"
                "Running in production with wrong environment detection is DANGEROUS.\n"
                "Please check your Kubernetes namespace configuration."
            )

        if parts[0] != "layer":
            raise KStackConfigurationError(
                f"Invalid namespace format: '{self._namespace}'\n"
                f"Namespace must start with 'layer-', got '{parts[0]}-'"
            )

        # Layer number should be second part
        try:
            int(parts[1])
        except ValueError:
            raise KStackConfigurationError(
                f"Invalid namespace format: '{self._namespace}'\n" f"Layer number must be numeric, got '{parts[1]}'"
            )

        # Environment is everything after "layer-{num}-"
        environment = "-".join(parts[2:])

        LOGGER.debug(f"Detected environment '{environment}' from namespace '{self._namespace}'")
        return environment

    def get_config_root(self) -> None:
        """
        Get config root - always None in-cluster.

        In-cluster, configuration comes from K8s ConfigMaps, not files.

        Returns
        -------
            None (configs come from ConfigMaps)

        """
        return None

    def get_vault_root(self) -> None:
        """
        Get vault root - always None in-cluster.

        Vaults do not exist in production! Secrets come from K8s Secret Manager.

        Returns
        -------
            None (no vault in cluster)

        """
        return None

    def __repr__(self) -> str:
        """String representation."""
        try:
            env = self.get_environment()
            return f"ClusterEnvironmentDetector(namespace='{self._namespace}', environment='{env}')"
        except Exception:
            return f"ClusterEnvironmentDetector(namespace='{self._namespace}')"
