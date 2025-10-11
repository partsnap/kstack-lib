"""
Runtime context detection for KStack.

Determines whether code is running inside a Kubernetes cluster or on a local machine.
This is the single source of truth for context detection used throughout kstack-lib.
"""

from functools import lru_cache
from pathlib import Path

from partsnap_logger.logging import psnap_get_logger

LOGGER = psnap_get_logger("kstack_lib.any.context")


@lru_cache(maxsize=1)
def is_in_cluster() -> bool:
    """
    Detect if running inside a Kubernetes cluster.

    Checks for the presence of the Kubernetes service account token file,
    which is mounted into every pod in a Kubernetes cluster.

    Returns:
    -------
        True if running inside K8s cluster, False otherwise

    Note:
    ----
        Result is cached since context doesn't change during runtime.

    Example:
    -------
        >>> from kstack_lib.any.context import is_in_cluster
        >>> if is_in_cluster():
        ...     print("Running in Kubernetes")
        ... else:
        ...     print("Running on local machine")

    """
    token_file = Path("/var/run/secrets/kubernetes.io/serviceaccount/token")
    in_cluster = token_file.exists()

    if in_cluster:
        LOGGER.debug("Detected in-cluster execution (Kubernetes)")
    else:
        LOGGER.debug("Detected local execution (dev machine)")

    return in_cluster
