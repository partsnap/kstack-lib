"""KStack layer type definitions."""

from enum import Enum


class KStackLayer(Enum):
    """
    KStack infrastructure layers.

    Layers are numbered from 0 (applications) to 3 (infrastructure).
    Enum values are descriptive names, namespace property returns actual K8s namespace.

    Layer Architecture:
    - LAYER_0_APPLICATIONS: User-facing applications (PartMaster, dashboards, frontends)
    - LAYER_1_TENANT_INFRA: Per-customer infrastructure (RDS, ElastiCache, S3, SQS)
    - LAYER_2_GLOBAL_SERVICES: Shared business logic (PartFinder, cross-tenant services)
    - LAYER_3_GLOBAL_INFRA: Foundation infrastructure (Redis, LocalStack, shared resources)
    """

    LAYER_0_APPLICATIONS = "layer-0-applications"
    LAYER_1_TENANT_INFRA = "layer-1-tenant-infra"
    LAYER_2_GLOBAL_SERVICES = "layer-2-global-services"
    LAYER_3_GLOBAL_INFRA = "layer-3-global-infra"

    @property
    def namespace(self) -> str:
        """
        Get the Kubernetes namespace for this layer.

        Returns the enum value, which is the K8s namespace name.

        Returns
        -------
            Namespace name (e.g., 'layer-3-global-infra')

        """
        return self.value

    @property
    def display_name(self) -> str:
        """
        Get human-readable display name.

        Returns
        -------
            Display name (e.g., 'Layer 3: Global Infrastructure')

        """
        display_names = {
            KStackLayer.LAYER_0_APPLICATIONS: "Layer 0: Applications",
            KStackLayer.LAYER_1_TENANT_INFRA: "Layer 1: Tenant Infrastructure",
            KStackLayer.LAYER_2_GLOBAL_SERVICES: "Layer 2: Global Services",
            KStackLayer.LAYER_3_GLOBAL_INFRA: "Layer 3: Global Infrastructure",
        }
        return display_names[self]

    @property
    def number(self) -> int:
        """
        Get layer number (0-3).

        Returns
        -------
            Layer number

        """
        return {
            KStackLayer.LAYER_0_APPLICATIONS: 0,
            KStackLayer.LAYER_1_TENANT_INFRA: 1,
            KStackLayer.LAYER_2_GLOBAL_SERVICES: 2,
            KStackLayer.LAYER_3_GLOBAL_INFRA: 3,
        }[self]

    @classmethod
    def from_namespace(cls, namespace: str) -> "KStackLayer":
        """
        Get layer from Kubernetes namespace name.

        Args:
        ----
            namespace: Kubernetes namespace (e.g., 'layer-3-global-infra')

        Returns:
        -------
            Corresponding KStackLayer

        Raises:
        ------
            ValueError: If namespace doesn't match any layer

        Example:
        -------
            >>> layer = KStackLayer.from_namespace('layer-3-global-infra')
            >>> layer == KStackLayer.LAYER_3_GLOBAL_INFRA
            True

        """
        for layer in cls:
            if layer.namespace == namespace:
                return layer
        raise ValueError(f"Unknown namespace: {namespace}")

    @classmethod
    def from_number(cls, num: int) -> "KStackLayer":
        """
        Get layer from number (0-3).

        Args:
        ----
            num: Layer number (0-3)

        Returns:
        -------
            Corresponding KStackLayer

        Raises:
        ------
            ValueError: If number is invalid

        """
        for layer in cls:
            if layer.number == num:
                return layer
        raise ValueError(f"Invalid layer number: {num}")

    @classmethod
    def from_string(cls, value: str) -> "KStackLayer":
        """
        Get layer from string (supports short aliases and full names).

        Accepts multiple formats:
        - Short aliases: 'layer0', 'layer1', 'layer2', 'layer3'
        - Full names: 'layer-0-applications', 'layer-1-tenant-infra', etc.
        - Numbers: '0', '1', '2', '3'

        Args:
        ----
            value: Layer string in any supported format

        Returns:
        -------
            Corresponding KStackLayer

        Raises:
        ------
            ValueError: If value doesn't match any layer

        Example:
        -------
            >>> KStackLayer.from_string('layer0')
            <KStackLayer.LAYER_0_APPLICATIONS: 'layer-0-applications'>
            >>> KStackLayer.from_string('layer-3-global-infra')
            <KStackLayer.LAYER_3_GLOBAL_INFRA: 'layer-3-global-infra'>
            >>> KStackLayer.from_string('3')
            <KStackLayer.LAYER_3_GLOBAL_INFRA: 'layer-3-global-infra'>

        """
        value_lower = value.lower().strip()

        # Try short aliases first (layer0, layer1, layer2, layer3)
        alias_map = {
            "layer0": cls.LAYER_0_APPLICATIONS,
            "layer1": cls.LAYER_1_TENANT_INFRA,
            "layer2": cls.LAYER_2_GLOBAL_SERVICES,
            "layer3": cls.LAYER_3_GLOBAL_INFRA,
        }
        if value_lower in alias_map:
            return alias_map[value_lower]

        # Try number (0, 1, 2, 3)
        if value_lower.isdigit():
            return cls.from_number(int(value_lower))

        # Try full enum value
        try:
            return cls(value_lower)
        except ValueError:
            pass

        # No match
        raise ValueError(
            f"Invalid layer: '{value}'. "
            f"Use: layer0, layer1, layer2, layer3 (or full names: layer-0-applications, etc.)"
        )


class LayerChoice(str, Enum):
    """Layer selection options including 'all' for CLI commands."""

    ALL = "all"
    LAYER0 = "0"
    LAYER1 = "1"
    LAYER2 = "2"
    LAYER3 = "3"
