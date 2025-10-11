"""Tests for types module."""

import pytest

from kstack_lib.types import KStackEnvironment, KStackLayer, LayerChoice


class TestKStackEnvironment:
    """Tests for KStackEnvironment enum."""

    def test_environment_values(self):
        """Test that environment enum values are correct."""
        assert KStackEnvironment.DEVELOPMENT.value == "dev"
        assert KStackEnvironment.TESTING.value == "test"
        assert KStackEnvironment.STAGING.value == "staging"
        assert KStackEnvironment.PRODUCTION.value == "prod"
        assert KStackEnvironment.SCRATCH.value == "scratch"
        assert KStackEnvironment.DATA_COLLECTION.value == "data-collection"

    def test_from_string_lowercase(self):
        """Test from_string with lowercase input."""
        assert KStackEnvironment.from_string("dev") == KStackEnvironment.DEVELOPMENT
        assert KStackEnvironment.from_string("test") == KStackEnvironment.TESTING
        assert KStackEnvironment.from_string("staging") == KStackEnvironment.STAGING
        assert KStackEnvironment.from_string("prod") == KStackEnvironment.PRODUCTION
        assert KStackEnvironment.from_string("scratch") == KStackEnvironment.SCRATCH
        assert KStackEnvironment.from_string("data-collection") == KStackEnvironment.DATA_COLLECTION

    def test_from_string_uppercase(self):
        """Test from_string with uppercase input."""
        assert KStackEnvironment.from_string("DEV") == KStackEnvironment.DEVELOPMENT
        assert KStackEnvironment.from_string("TEST") == KStackEnvironment.TESTING
        assert KStackEnvironment.from_string("STAGING") == KStackEnvironment.STAGING
        assert KStackEnvironment.from_string("PROD") == KStackEnvironment.PRODUCTION

    def test_from_string_mixed_case(self):
        """Test from_string with mixed case input."""
        assert KStackEnvironment.from_string("Dev") == KStackEnvironment.DEVELOPMENT
        assert KStackEnvironment.from_string("TeSt") == KStackEnvironment.TESTING
        assert KStackEnvironment.from_string("PrOd") == KStackEnvironment.PRODUCTION

    def test_from_string_with_whitespace(self):
        """Test from_string strips whitespace."""
        assert KStackEnvironment.from_string("  dev  ") == KStackEnvironment.DEVELOPMENT
        assert KStackEnvironment.from_string("\ttest\n") == KStackEnvironment.TESTING

    def test_from_string_invalid(self):
        """Test from_string raises ValueError for invalid input."""
        with pytest.raises(ValueError, match="Invalid environment"):
            KStackEnvironment.from_string("invalid-environment")

        with pytest.raises(ValueError, match="Valid environments"):
            KStackEnvironment.from_string("testing")  # Old name should fail

    def test_all_environments(self):
        """Test all_environments returns all environment enums."""
        environments = KStackEnvironment.all_environments()
        assert len(environments) == 6  # Now includes PRODUCTION
        assert KStackEnvironment.DEVELOPMENT in environments
        assert KStackEnvironment.TESTING in environments
        assert KStackEnvironment.STAGING in environments
        assert KStackEnvironment.PRODUCTION in environments
        assert KStackEnvironment.SCRATCH in environments
        assert KStackEnvironment.DATA_COLLECTION in environments

    def test_iteration(self):
        """Test that we can iterate over environments."""
        environments = list(KStackEnvironment)
        assert len(environments) == 6  # Now includes PRODUCTION


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
        assert KStackLayer.from_namespace("layer-0-applications") == KStackLayer.LAYER_0_APPLICATIONS
        assert KStackLayer.from_namespace("layer-1-tenant-infra") == KStackLayer.LAYER_1_TENANT_INFRA
        assert KStackLayer.from_namespace("layer-2-global-services") == KStackLayer.LAYER_2_GLOBAL_SERVICES
        assert KStackLayer.from_namespace("layer-3-global-infra") == KStackLayer.LAYER_3_GLOBAL_INFRA

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
