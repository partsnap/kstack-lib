"""
Exception definitions for KStack (backward compatibility shim).

This module re-exports exceptions from kstack_lib.any.exceptions for backward compatibility.
New code should import directly from kstack_lib.any.exceptions.
"""

# Re-export with old names for backward compatibility
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

__all__ = [
    "KStackError",
    "LayerAccessError",
    "ServiceNotFoundError",
    "ConfigurationError",
    "RouteError",
    "KStackEnvironmentError",
]
