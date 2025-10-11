"""
KStack ConfigMap access layer.

Provides a clean API for accessing layer-specific ConfigMaps with automatic
namespace detection when running in Kubernetes.
"""

import os
import subprocess
from pathlib import Path

from kstack_lib.types import KStackEnvironment, KStackLayer


class ConfigMap:
    """
    Access layer-specific ConfigMaps with automatic namespace detection.

    Examples
    --------
        # Explicit layer (required when running locally)
        >>> cfg = ConfigMap(layer=KStackLayer.LAYER_3_GLOBAL_INFRA)
        >>> route = cfg.get_active_route()
        'development'

        # Auto-detect layer when running in Kubernetes
        >>> cfg = ConfigMap()  # Detects current namespace
        >>> route = cfg.get_active_route()
        'development'

        # Access layer information
        >>> cfg.layer.namespace
        'layer-3-cloud'
        >>> cfg.layer.display_name
        'Layer 3: Global Infrastructure'

    """

    def __init__(self, layer: KStackLayer | None = None, environment: KStackEnvironment | None = None):
        """
        Initialize ConfigMap accessor.

        Args:
        ----
            layer: KStack layer to access. If not provided, auto-detects
                   current layer when running in Kubernetes pod.
            environment: KStack environment (dev, testing, staging, production).
                        If not provided, uses get_active_route() for compatibility.

        Raises:
        ------
            ValueError: If layer is not provided and auto-detection fails
                       (not running in Kubernetes or unknown namespace)

        Example:
        -------
            >>> # Explicit layer and environment
            >>> cfg = ConfigMap(layer=KStackLayer.LAYER_3_GLOBAL_INFRA, environment=KStackEnvironment.DEVELOPMENT)

            >>> # Explicit layer (environment auto-detected)
            >>> cfg = ConfigMap(layer=KStackLayer.LAYER_3_GLOBAL_INFRA)

            >>> # Auto-detect (only works in Kubernetes)
            >>> cfg = ConfigMap()

        """
        if layer is None:
            # Try to auto-detect current layer
            namespace = self._detect_current_namespace()
            if namespace is None:
                raise ValueError(
                    "Cannot auto-detect layer. You must specify layer explicitly "
                    "when running outside Kubernetes. Example: "
                    "ConfigMap(layer=KStackLayer.LAYER_3_GLOBAL_INFRA)"
                )
            try:
                layer = KStackLayer.from_namespace(namespace)
            except ValueError as e:
                raise ValueError(f"Unknown namespace: {namespace}. Cannot determine layer.") from e

        self.layer = layer
        self._environment = environment

    @staticmethod
    def running_in_k8s() -> bool:
        """
        Check if currently running inside a Kubernetes pod.

        Returns:
        -------
            True if running in Kubernetes, False otherwise

        Example:
        -------
            >>> if ConfigMap.running_in_k8s():
            ...     cfg = ConfigMap()  # Auto-detect
            ... else:
            ...     cfg = ConfigMap(layer=KStackLayer.LAYER_3_GLOBAL_INFRA)

        """
        namespace_file = Path("/var/run/secrets/kubernetes.io/serviceaccount/namespace")
        return namespace_file.exists()

    @staticmethod
    def _detect_current_namespace() -> str | None:
        """
        Detect current Kubernetes namespace when running in a pod.

        Returns
        -------
            Current namespace if running in Kubernetes, None otherwise

        """
        namespace_file = Path("/var/run/secrets/kubernetes.io/serviceaccount/namespace")
        try:
            return namespace_file.read_text().strip()
        except FileNotFoundError:
            return None

    @property
    def namespace(self) -> str:
        """
        Get the Kubernetes namespace for this layer.

        Returns:
        -------
            Namespace name (e.g., 'layer-3-cloud')

        Example:
        -------
            >>> cfg = ConfigMap(layer=KStackLayer.LAYER_3_GLOBAL_INFRA)
            >>> cfg.namespace
            'layer-3-cloud'

        """
        return self.layer.namespace

    @property
    def environment(self) -> KStackEnvironment:
        """
        Get the active environment for this layer.

        Returns the environment by checking (in order):
        1. Environment passed to __init__
        2. KSTACK_ROUTE environment variable mapped to KStackEnvironment
        3. kstack-route ConfigMap mapped to KStackEnvironment
        4. Falls back to KStackEnvironment.DEVELOPMENT

        Returns:
        -------
            Active environment (DEVELOPMENT, TESTING, STAGING, PRODUCTION, SCRATCH, DATA_COLLECTION)

        Example:
        -------
            >>> cfg = ConfigMap(layer=KStackLayer.LAYER_3_GLOBAL_INFRA, environment=KStackEnvironment.DEVELOPMENT)
            >>> cfg.environment
            <KStackEnvironment.DEVELOPMENT: 'dev'>

        """
        if self._environment is not None:
            return self._environment

        # Fall back to route-based system and map to environment
        route = self.get_active_route()

        # Map route strings to KStackEnvironment (with backward compatibility)
        route_to_env = {
            "development": KStackEnvironment.DEVELOPMENT,
            "dev": KStackEnvironment.DEVELOPMENT,
            "testing": KStackEnvironment.TESTING,  # Backward compatibility
            "test": KStackEnvironment.TESTING,
            "staging": KStackEnvironment.STAGING,
            "production": KStackEnvironment.PRODUCTION,  # Backward compatibility
            "prod": KStackEnvironment.PRODUCTION,
            "scratch": KStackEnvironment.SCRATCH,
            "data-collection": KStackEnvironment.DATA_COLLECTION,
        }

        return route_to_env.get(route, KStackEnvironment.DEVELOPMENT)

    def get_active_route(self) -> str:
        """
        Get the currently active route for this layer.

        Returns the active route by checking (in order):
        1. KSTACK_ROUTE environment variable
        2. kstack-route ConfigMap in layer's namespace
        3. Falls back to 'development'

        Returns:
        -------
            Active route name (e.g., 'development', 'testing', 'staging')

        Example:
        -------
            >>> cfg = ConfigMap(layer=KStackLayer.LAYER_3_GLOBAL_INFRA)
            >>> route = cfg.get_active_route()
            'development'

        """
        # 1. Check environment variable first (fastest)
        route = os.environ.get("KSTACK_ROUTE")
        if route:
            return route

        # 2. Query ConfigMap in layer's namespace
        try:
            result = subprocess.run(
                [
                    "kubectl",
                    "get",
                    "configmap",
                    "kstack-route",
                    "-n",
                    self.layer.namespace,
                    "-o",
                    "jsonpath={.data.active-route}",
                ],
                capture_output=True,
                text=True,
                check=True,
                timeout=5,
            )
            route = result.stdout.strip()
            if route:
                return route
        except (subprocess.CalledProcessError, subprocess.TimeoutExpired, FileNotFoundError):
            # kubectl not available or ConfigMap doesn't exist
            pass

        # 3. Fall back to development
        return "development"

    def set_active_route(self, route_name: str) -> None:
        """
        Set the active route for this layer.

        Updates the kstack-route ConfigMap in the layer's namespace.

        Args:
        ----
            route_name: Route to activate (e.g., 'development', 'testing')

        Raises:
        ------
            subprocess.CalledProcessError: If kubectl command fails

        Example:
        -------
            >>> cfg = ConfigMap(layer=KStackLayer.LAYER_3_GLOBAL_INFRA)
            >>> cfg.set_active_route('testing')

        """
        subprocess.run(
            [
                "kubectl",
                "patch",
                "configmap",
                "kstack-route",
                "-n",
                self.layer.namespace,
                "--type",
                "merge",
                "-p",
                f'{{"data":{{"active-route":"{route_name}"}}}}',
            ],
            check=True,
            timeout=10,
        )

        # Also update environment variable for current process
        os.environ["KSTACK_ROUTE"] = route_name

    def get_value(self, configmap_name: str, key: str) -> str | None:
        """
        Get a value from any ConfigMap in this layer's namespace.

        Args:
        ----
            configmap_name: Name of the ConfigMap
            key: Key to retrieve from ConfigMap data

        Returns:
        -------
            Value for the key, or None if not found

        Example:
        -------
            >>> cfg = ConfigMap(layer=KStackLayer.LAYER_3_GLOBAL_INFRA)
            >>> instance = cfg.get_value('localstack-proxy-config', 'active-instance')
            'development'

        """
        try:
            result = subprocess.run(
                [
                    "kubectl",
                    "get",
                    "configmap",
                    configmap_name,
                    "-n",
                    self.layer.namespace,
                    "-o",
                    f"jsonpath={{.data.{key}}}",
                ],
                capture_output=True,
                text=True,
                check=True,
                timeout=5,
            )
            return result.stdout.strip() or None
        except (subprocess.CalledProcessError, subprocess.TimeoutExpired, FileNotFoundError):
            return None

    def __repr__(self) -> str:
        """Return string representation of ConfigMap accessor."""
        return (
            f"ConfigMap(layer={self.layer.value}, "
            f"namespace={self.layer.namespace}, "
            f"environment={self.environment.value})"
        )
