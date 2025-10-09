"""Tests for ConfigMap and KStackLayer."""

import os
import subprocess
from unittest.mock import MagicMock, patch

import pytest

from kstack_lib.config import ConfigMap, KStackLayer


class TestKStackLayer:
    """Tests for KStackLayer enum."""

    def test_layer_values(self):
        """Test that layer enum values are semantic."""
        assert KStackLayer.LAYER_0_APPLICATIONS.value == "layer-0-applications"
        assert KStackLayer.LAYER_1_TENANT_INFRA.value == "layer-1-tenant-infra"
        assert KStackLayer.LAYER_2_GLOBAL_SERVICES.value == "layer-2-global-services"
        assert KStackLayer.LAYER_3_GLOBAL_INFRA.value == "layer-3-global-infra"

    def test_namespace_property(self):
        """Test that namespace property maps to correct K8s namespaces."""
        assert KStackLayer.LAYER_0_APPLICATIONS.namespace == "layer-0"
        assert KStackLayer.LAYER_1_TENANT_INFRA.namespace == "layer-1"
        assert KStackLayer.LAYER_2_GLOBAL_SERVICES.namespace == "layer-2-global"
        assert KStackLayer.LAYER_3_GLOBAL_INFRA.namespace == "layer-3-cloud"

    def test_display_name_property(self):
        """Test that display names are human-readable."""
        assert KStackLayer.LAYER_0_APPLICATIONS.display_name == "Layer 0: Applications"
        assert KStackLayer.LAYER_1_TENANT_INFRA.display_name == "Layer 1: Tenant Infrastructure"
        assert KStackLayer.LAYER_2_GLOBAL_SERVICES.display_name == "Layer 2: Global Services"
        assert KStackLayer.LAYER_3_GLOBAL_INFRA.display_name == "Layer 3: Global Infrastructure"

    def test_number_property(self):
        """Test that layer numbers are correct."""
        assert KStackLayer.LAYER_0_APPLICATIONS.number == 0
        assert KStackLayer.LAYER_1_TENANT_INFRA.number == 1
        assert KStackLayer.LAYER_2_GLOBAL_SERVICES.number == 2
        assert KStackLayer.LAYER_3_GLOBAL_INFRA.number == 3

    def test_from_namespace(self):
        """Test reverse lookup from namespace to layer."""
        layer = KStackLayer.from_namespace("layer-3-cloud")
        assert layer == KStackLayer.LAYER_3_GLOBAL_INFRA

        layer = KStackLayer.from_namespace("layer-2-global")
        assert layer == KStackLayer.LAYER_2_GLOBAL_SERVICES

        layer = KStackLayer.from_namespace("layer-1")
        assert layer == KStackLayer.LAYER_1_TENANT_INFRA

        layer = KStackLayer.from_namespace("layer-0")
        assert layer == KStackLayer.LAYER_0_APPLICATIONS

    def test_from_namespace_invalid(self):
        """Test that invalid namespace raises ValueError."""
        with pytest.raises(ValueError, match="Unknown namespace"):
            KStackLayer.from_namespace("invalid-namespace")

    def test_from_number(self):
        """Test lookup from number to layer."""
        assert KStackLayer.from_number(0) == KStackLayer.LAYER_0_APPLICATIONS
        assert KStackLayer.from_number(1) == KStackLayer.LAYER_1_TENANT_INFRA
        assert KStackLayer.from_number(2) == KStackLayer.LAYER_2_GLOBAL_SERVICES
        assert KStackLayer.from_number(3) == KStackLayer.LAYER_3_GLOBAL_INFRA

    def test_from_number_invalid(self):
        """Test that invalid number raises ValueError."""
        with pytest.raises(ValueError, match="Invalid layer number"):
            KStackLayer.from_number(99)


class TestConfigMap:
    """Tests for ConfigMap class."""

    def test_init_with_explicit_layer(self):
        """Test ConfigMap initialization with explicit layer."""
        cfg = ConfigMap(layer=KStackLayer.LAYER_3_GLOBAL_INFRA)
        assert cfg.layer == KStackLayer.LAYER_3_GLOBAL_INFRA

    def test_init_with_auto_detect_success(self, tmp_path):
        """Test ConfigMap initialization with auto-detection."""
        namespace_file = tmp_path / "namespace"
        namespace_file.write_text("layer-3-cloud")

        with patch("pathlib.Path.read_text", return_value="layer-3-cloud"):
            cfg = ConfigMap()
            assert cfg.layer == KStackLayer.LAYER_3_GLOBAL_INFRA

    def test_init_with_auto_detect_failure(self):
        """Test ConfigMap initialization when auto-detection fails."""
        with patch("builtins.open", side_effect=FileNotFoundError):
            with pytest.raises(ValueError, match="Cannot auto-detect layer"):
                ConfigMap()

    def test_get_active_route_from_env(self):
        """Test get_active_route reads from environment variable."""
        cfg = ConfigMap(layer=KStackLayer.LAYER_3_GLOBAL_INFRA)

        with patch.dict(os.environ, {"KSTACK_ROUTE": "testing"}):
            route = cfg.get_active_route()
            assert route == "testing"

    @patch("subprocess.run")
    def test_get_active_route_from_configmap(self, mock_run):
        """Test get_active_route reads from ConfigMap."""
        cfg = ConfigMap(layer=KStackLayer.LAYER_3_GLOBAL_INFRA)

        # Mock kubectl success
        mock_run.return_value = MagicMock(stdout="development", returncode=0)

        with patch.dict(os.environ, clear=True):  # Clear KSTACK_ROUTE
            route = cfg.get_active_route()
            assert route == "development"

        # Verify kubectl was called with correct namespace
        mock_run.assert_called_once()
        call_args = mock_run.call_args[0][0]
        assert "layer-3-cloud" in call_args
        assert "kstack-route" in call_args

    @patch("subprocess.run")
    def test_get_active_route_fallback(self, mock_run):
        """Test get_active_route falls back to development."""
        cfg = ConfigMap(layer=KStackLayer.LAYER_3_GLOBAL_INFRA)

        # Mock kubectl failure
        mock_run.side_effect = subprocess.CalledProcessError(1, "kubectl")

        with patch.dict(os.environ, clear=True):
            route = cfg.get_active_route()
            assert route == "development"

    @patch("subprocess.run")
    def test_set_active_route(self, mock_run):
        """Test set_active_route updates ConfigMap and env var."""
        cfg = ConfigMap(layer=KStackLayer.LAYER_3_GLOBAL_INFRA)

        with patch.dict(os.environ, clear=True):
            cfg.set_active_route("testing")

            # Verify kubectl was called
            mock_run.assert_called_once()
            call_args = mock_run.call_args[0][0]
            assert "kubectl" in call_args
            assert "patch" in call_args
            assert "configmap" in call_args
            assert "kstack-route" in call_args
            assert "layer-3-cloud" in call_args
            assert "testing" in " ".join(call_args)

            # Verify environment variable was set
            assert os.environ["KSTACK_ROUTE"] == "testing"

    @patch("subprocess.run")
    def test_get_value(self, mock_run):
        """Test get_value reads from ConfigMap."""
        cfg = ConfigMap(layer=KStackLayer.LAYER_3_GLOBAL_INFRA)

        mock_run.return_value = MagicMock(stdout="development", returncode=0)

        value = cfg.get_value("kstack-route", "active-route")
        assert value == "development"

        # Verify kubectl was called correctly
        call_args = mock_run.call_args[0][0]
        assert "kstack-route" in call_args
        assert "layer-3-cloud" in call_args
        assert "active-route" in " ".join(call_args)

    @patch("subprocess.run")
    def test_get_value_not_found(self, mock_run):
        """Test get_value returns None when value not found."""
        cfg = ConfigMap(layer=KStackLayer.LAYER_3_GLOBAL_INFRA)

        mock_run.side_effect = subprocess.CalledProcessError(1, "kubectl")

        value = cfg.get_value("nonexistent", "key")
        assert value is None

    def test_repr(self):
        """Test string representation of ConfigMap."""
        cfg = ConfigMap(layer=KStackLayer.LAYER_3_GLOBAL_INFRA)
        repr_str = repr(cfg)
        assert "ConfigMap" in repr_str
        assert "layer-3-global-infra" in repr_str
        assert "layer-3-cloud" in repr_str

    def test_different_layers_different_namespaces(self):
        """Test that different layers use different namespaces."""
        cfg_layer3 = ConfigMap(layer=KStackLayer.LAYER_3_GLOBAL_INFRA)
        cfg_layer2 = ConfigMap(layer=KStackLayer.LAYER_2_GLOBAL_SERVICES)

        assert cfg_layer3.layer.namespace == "layer-3-cloud"
        assert cfg_layer2.layer.namespace == "layer-2-global"
