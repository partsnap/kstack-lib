"""Tests for KStack service enums and updated service discovery APIs."""

import pytest

from kstack_lib import LayerAccessError, ServiceNotFoundError
from kstack_lib.config import ConfigMap, KStackRedisDatabase, get_redis_config
from kstack_lib.types import KStackLayer, KStackLocalStackService


class TestKStackRedisDatabase:
    """Tests for KStackRedisDatabase enum."""

    def test_redis_database_values(self):
        """Test that Redis database enum values match expected strings."""
        assert KStackRedisDatabase.PART_RAW.value == "part-raw"
        assert KStackRedisDatabase.PART_AUDIT.value == "part-audit"

    def test_redis_database_display_names(self):
        """Test human-readable display names."""
        assert KStackRedisDatabase.PART_RAW.display_name == "Part Raw Data"
        assert KStackRedisDatabase.PART_AUDIT.display_name == "Part Audit Logs"

    def test_redis_database_layer(self):
        """Test that all Redis databases are in Layer 3."""
        assert KStackRedisDatabase.PART_RAW.layer == 3
        assert KStackRedisDatabase.PART_AUDIT.layer == 3


class TestKStackLocalStackService:
    """Tests for KStackLocalStackService enum."""

    def test_localstack_service_values(self):
        """Test LocalStack service enum values."""
        assert KStackLocalStackService.DEFAULT.value == "default"

    def test_localstack_service_display_name(self):
        """Test LocalStack display name."""
        assert KStackLocalStackService.DEFAULT.display_name == "LocalStack (AWS Services)"

    def test_localstack_service_layer(self):
        """Test that LocalStack is in Layer 3."""
        assert KStackLocalStackService.DEFAULT.layer == 3


class TestGetRedisConfigWithEnums:
    """Tests for updated get_redis_config() API with ConfigMap and enums."""

    def test_layer_validation_rejects_wrong_layer(self):
        """Test that accessing Redis from Layer 0 raises LayerAccessError."""
        cfg = ConfigMap(layer=KStackLayer.LAYER_0_APPLICATIONS)

        with pytest.raises(LayerAccessError, match="Redis databases are only available in Layer 3"):
            get_redis_config(cfg, KStackRedisDatabase.PART_RAW)

    def test_layer_validation_rejects_layer1(self):
        """Test that accessing Redis from Layer 1 raises LayerAccessError."""
        cfg = ConfigMap(layer=KStackLayer.LAYER_1_TENANT_INFRA)

        with pytest.raises(LayerAccessError, match="Redis databases are only available in Layer 3"):
            get_redis_config(cfg, KStackRedisDatabase.PART_AUDIT)

    def test_layer_validation_rejects_layer2(self):
        """Test that accessing Redis from Layer 2 raises LayerAccessError."""
        cfg = ConfigMap(layer=KStackLayer.LAYER_2_GLOBAL_SERVICES)

        with pytest.raises(LayerAccessError, match="Redis databases are only available in Layer 3"):
            get_redis_config(cfg, KStackRedisDatabase.PART_RAW)

    def test_layer_validation_accepts_layer3(self):
        """Test that accessing Redis from Layer 3 is allowed (even if config not found)."""
        cfg = ConfigMap(layer=KStackLayer.LAYER_3_GLOBAL_INFRA)

        # Should not raise layer validation error, but may raise config not found
        with pytest.raises(ServiceNotFoundError) as exc_info:
            get_redis_config(cfg, KStackRedisDatabase.PART_RAW)

        # Should be config not found error, not layer validation error
        assert "only available in Layer 3" not in str(exc_info.value)
        assert "configuration not found" in str(exc_info.value).lower()

    def test_enum_parameter_converts_to_string(self):
        """Test that KStackRedisDatabase enum is properly converted."""
        cfg = ConfigMap(layer=KStackLayer.LAYER_3_GLOBAL_INFRA)

        # Should accept enum and convert to string internally
        with pytest.raises(ServiceNotFoundError, match="configuration not found"):
            # Will fail due to no actual config, but validates enum handling
            get_redis_config(cfg, KStackRedisDatabase.PART_AUDIT)

    def test_backward_compatibility_with_string(self):
        """Test that old string-based API still works."""
        # Old API: get_redis_config(database='part-raw')
        with pytest.raises(ServiceNotFoundError, match="configuration not found"):
            get_redis_config(database="part-raw")

    def test_backward_compatibility_without_configmap(self):
        """Test that calling without ConfigMap defaults to Layer 3."""
        # Should create default Layer 3 ConfigMap internally
        with pytest.raises(ServiceNotFoundError, match="configuration not found"):
            get_redis_config(database="part-audit")

    def test_none_database_defaults_to_part_raw(self):
        """Test that None database parameter defaults to part-raw."""
        cfg = ConfigMap(layer=KStackLayer.LAYER_3_GLOBAL_INFRA)

        with pytest.raises(ServiceNotFoundError) as exc_info:
            get_redis_config(cfg, None)

        # Should try to find part-raw (the default)
        assert "part-raw" in str(exc_info.value)


class TestServiceEnumIntegration:
    """Integration tests for service enums with ConfigMap."""

    def test_can_import_all_enums_from_config(self):
        """Test that all service enums are exported from kstack_lib.config."""
        from kstack_lib.config import KStackLocalStackService, KStackRedisDatabase

        assert KStackRedisDatabase.PART_RAW.value == "part-raw"
        assert KStackLocalStackService.DEFAULT.value == "default"

    def test_can_import_all_enums_from_types(self):
        """Test that all service enums are exported from kstack_lib.types."""
        from kstack_lib.types import KStackLocalStackService, KStackRedisDatabase

        assert KStackRedisDatabase.PART_AUDIT.value == "part-audit"
        assert KStackLocalStackService.DEFAULT.value == "default"
