"""
Local - Components that run ONLY on development machines.

This module contains code that will raise KStackEnvironmentError if imported in-cluster.
Includes vault management, local environment detection, and file-based configuration.
"""

from kstack_lib.local.security.vault import KStackVault, get_vault_root

__all__ = [
    "KStackVault",
    "get_vault_root",
]
