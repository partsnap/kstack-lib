"""
KStack Library - Infrastructure client library for PartSnap services.

This library provides context-aware infrastructure components:
- IoC Container: Automatic dependency injection based on runtime context
- Cloud Abstraction Layer (CAL): Unified interface for cloud services
- Configuration management from vault files (local) or Kubernetes secrets (cluster)
- Import guards: Prevents accidental misuse of context-specific code

Designed with a three-tier architecture (any/local/cluster) for maximum safety.
"""

# ============================================================================
# CORE EXPORTS (from any/)
# ============================================================================

from kstack_lib.any.exceptions import (
    KStackConfigurationError as ConfigurationError,
)
from kstack_lib.any.exceptions import (
    KStackEnvironmentError,
    KStackError,
)
from kstack_lib.any.exceptions import (
    KStackLayerAccessError as LayerAccessError,
)
from kstack_lib.any.exceptions import (
    KStackRouteError as RouteError,
)
from kstack_lib.any.exceptions import (
    KStackServiceNotFoundError as ServiceNotFoundError,
)
from kstack_lib.any.utils import run_command

try:
    from kstack_lib._version import __version__
except ImportError:
    __version__ = "0.0.0.dev0"

__all__ = [
    # Exceptions
    "KStackError",
    "LayerAccessError",
    "ServiceNotFoundError",
    "ConfigurationError",
    "RouteError",
    "KStackEnvironmentError",
    # Utils
    "run_command",
    # Version
    "__version__",
]
