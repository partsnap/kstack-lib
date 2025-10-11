"""Base class for cluster-only components with mockable guard."""

from functools import lru_cache

from kstack_lib.any.context import is_in_cluster
from kstack_lib.any.exceptions import KStackEnvironmentError


class ClusterBase:
    """
    Base class for all cluster-only components.

    Provides a mockable guard method that can be patched in tests.
    """

    @classmethod
    @lru_cache(maxsize=1)
    def _check_cluster_context(cls) -> None:
        """
        Verify running in cluster context.

        Raises:
        ------
            KStackEnvironmentError: If not running in Kubernetes cluster

        Note:
        ----
            This method is cached and can be mocked in tests using:
            `@patch.object(ClusterBase, '_check_cluster_context')`

        """
        if not is_in_cluster():
            raise KStackEnvironmentError(
                "Cannot use cluster component outside Kubernetes cluster.\n"
                "\n"
                "This component is designed to run ONLY inside Kubernetes pods.\n"
                "If you're on a dev machine, use kstack_lib.local.* instead.\n"
                "\n"
                "This error prevents accidental use of cluster-specific code in the wrong context."
            )

    def __init__(self) -> None:
        """Initialize cluster component and verify context."""
        self._check_cluster_context()
