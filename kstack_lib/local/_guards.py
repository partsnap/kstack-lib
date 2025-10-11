"""
Import guard for local-only modules.

This module MUST be imported at the top of every module in kstack_lib.local/.
It raises KStackEnvironmentError if the code is imported inside a Kubernetes cluster.

Usage:
    # At the top of every local module:
    from kstack_lib.local import _guards  # noqa: F401
"""

from kstack_lib.any.context import is_in_cluster
from kstack_lib.any.exceptions import KStackEnvironmentError

# Dummy symbol for import (the guard runs on module load)
_enforce_local = True

if is_in_cluster():
    raise KStackEnvironmentError(
        "Cannot import local module inside Kubernetes cluster.\n"
        "\n"
        "This module is designed to run ONLY on local dev machines.\n"
        "If you're inside a K8s pod, use kstack_lib.cluster.* instead.\n"
        "\n"
        "This error prevents accidental use of local-specific code (like vault) in production."
    )
