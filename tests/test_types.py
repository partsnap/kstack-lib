"""Tests for types module."""

import pytest

from kstack_lib.types import KStackLayer, KStackRoute, LayerChoice


class TestKStackRoute:
    """Tests for KStackRoute enum."""

    def test_route_values(self):
        """Test that route enum values are correct."""
        assert KStackRoute.DEVELOPMENT.value == "development"
        assert KStackRoute.TESTING.value == "testing"
        assert KStackRoute.STAGING.value == "staging"
        assert KStackRoute.SCRATCH.value == "scratch"
        assert KStackRoute.DATA_COLLECTION.value == "data-collection"

    def test_from_string_lowercase(self):
        """Test from_string with lowercase input."""
        assert KStackRoute.from_string("development") == KStackRoute.DEVELOPMENT
        assert KStackRoute.from_string("testing") == KStackRoute.TESTING
        assert KStackRoute.from_string("staging") == KStackRoute.STAGING
        assert KStackRoute.from_string("scratch") == KStackRoute.SCRATCH
        assert KStackRoute.from_string("data-collection") == KStackRoute.DATA_COLLECTION

    def test_from_string_uppercase(self):
        """Test from_string with uppercase input."""
        assert KStackRoute.from_string("DEVELOPMENT") == KStackRoute.DEVELOPMENT
        assert KStackRoute.from_string("TESTING") == KStackRoute.TESTING
        assert KStackRoute.from_string("STAGING") == KStackRoute.STAGING

    def test_from_string_mixed_case(self):
        """Test from_string with mixed case input."""
        assert KStackRoute.from_string("Development") == KStackRoute.DEVELOPMENT
        assert KStackRoute.from_string("TeStInG") == KStackRoute.TESTING

    def test_from_string_with_whitespace(self):
        """Test from_string strips whitespace."""
        assert KStackRoute.from_string("  development  ") == KStackRoute.DEVELOPMENT
        assert KStackRoute.from_string("\ttesting\n") == KStackRoute.TESTING

    def test_from_string_invalid(self):
        """Test from_string raises ValueError for invalid input."""
        with pytest.raises(ValueError, match="Invalid route"):
            KStackRoute.from_string("invalid-route")

        with pytest.raises(ValueError, match="Valid routes"):
            KStackRoute.from_string("production")

    def test_all_routes(self):
        """Test all_routes returns all route enums."""
        routes = KStackRoute.all_routes()
        assert len(routes) == 5
        assert KStackRoute.DEVELOPMENT in routes
        assert KStackRoute.TESTING in routes
        assert KStackRoute.STAGING in routes
        assert KStackRoute.SCRATCH in routes
        assert KStackRoute.DATA_COLLECTION in routes

    def test_iteration(self):
        """Test that we can iterate over routes."""
        routes = list(KStackRoute)
        assert len(routes) == 5


class TestKStackLayerFromString:
    """Tests for KStackLayer.from_string method."""

    def test_from_string_short_aliases(self):
        """Test from_string with short aliases like 'layer0'."""
        assert KStackLayer.from_string("layer0") == KStackLayer.LAYER_0_APPLICATIONS
        assert KStackLayer.from_string("layer1") == KStackLayer.LAYER_1_TENANT_INFRA
        assert KStackLayer.from_string("layer2") == KStackLayer.LAYER_2_GLOBAL_SERVICES
        assert KStackLayer.from_string("layer3") == KStackLayer.LAYER_3_GLOBAL_INFRA

    def test_from_string_numbers(self):
        """Test from_string with numeric strings."""
        assert KStackLayer.from_string("0") == KStackLayer.LAYER_0_APPLICATIONS
        assert KStackLayer.from_string("1") == KStackLayer.LAYER_1_TENANT_INFRA
        assert KStackLayer.from_string("2") == KStackLayer.LAYER_2_GLOBAL_SERVICES
        assert KStackLayer.from_string("3") == KStackLayer.LAYER_3_GLOBAL_INFRA

    def test_from_string_full_names(self):
        """Test from_string with full layer names."""
        assert KStackLayer.from_string("layer-0-applications") == KStackLayer.LAYER_0_APPLICATIONS
        assert KStackLayer.from_string("layer-1-tenant-infra") == KStackLayer.LAYER_1_TENANT_INFRA
        assert KStackLayer.from_string("layer-2-global-services") == KStackLayer.LAYER_2_GLOBAL_SERVICES
        assert KStackLayer.from_string("layer-3-global-infra") == KStackLayer.LAYER_3_GLOBAL_INFRA

    def test_from_namespace_method(self):
        """Test from_namespace with Kubernetes namespace names."""
        assert KStackLayer.from_namespace("layer-0") == KStackLayer.LAYER_0_APPLICATIONS
        assert KStackLayer.from_namespace("layer-1") == KStackLayer.LAYER_1_TENANT_INFRA
        assert KStackLayer.from_namespace("layer-2-global") == KStackLayer.LAYER_2_GLOBAL_SERVICES
        assert KStackLayer.from_namespace("layer-3-cloud") == KStackLayer.LAYER_3_GLOBAL_INFRA

    def test_from_string_uppercase(self):
        """Test from_string is case-insensitive."""
        assert KStackLayer.from_string("LAYER0") == KStackLayer.LAYER_0_APPLICATIONS
        assert KStackLayer.from_string("Layer1") == KStackLayer.LAYER_1_TENANT_INFRA

    def test_from_string_with_whitespace(self):
        """Test from_string strips whitespace."""
        assert KStackLayer.from_string("  layer0  ") == KStackLayer.LAYER_0_APPLICATIONS
        assert KStackLayer.from_string("\tlayer1\n") == KStackLayer.LAYER_1_TENANT_INFRA

    def test_from_string_invalid(self):
        """Test from_string raises ValueError for invalid input."""
        with pytest.raises(ValueError, match="Invalid layer"):
            KStackLayer.from_string("invalid-layer")

        with pytest.raises(ValueError, match="Invalid layer"):
            KStackLayer.from_string("layer99")

        with pytest.raises(ValueError, match="Invalid layer"):
            KStackLayer.from_string("5")


class TestLayerChoice:
    """Tests for LayerChoice enum."""

    def test_layer_choice_values(self):
        """Test LayerChoice enum values."""
        assert LayerChoice.ALL.value == "all"
        assert LayerChoice.LAYER0.value == "0"
        assert LayerChoice.LAYER1.value == "1"
        assert LayerChoice.LAYER2.value == "2"
        assert LayerChoice.LAYER3.value == "3"

    def test_iteration(self):
        """Test that we can iterate over layer choices."""
        choices = list(LayerChoice)
        assert len(choices) == 5
        assert LayerChoice.ALL in choices
