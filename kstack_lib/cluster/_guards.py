"""
Import guard for cluster-only modules.

This module MUST be imported at the top of every module in kstack_lib.cluster/.
It raises KStackEnvironmentError if the code is imported outside a Kubernetes cluster.

Usage:
    # At the top of every cluster module:
    from kstack_lib.cluster import _guards  # noqa: F401
"""

from kstack_lib.any.context import is_in_cluster
from kstack_lib.any.exceptions import KStackEnvironmentError

# Dummy symbol for import (the guard runs on module load)
_enforce_cluster = True

if not is_in_cluster():
    raise KStackEnvironmentError(
        "Cannot import cluster module outside Kubernetes cluster.\n"
        "\n"
        "This module is designed to run ONLY inside Kubernetes pods.\n"
        "If you're on a dev machine, use kstack_lib.local.* instead.\n"
        "\n"
        "This error prevents accidental use of cluster-specific code in the wrong context."
    )
