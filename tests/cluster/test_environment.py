"""Tests for cluster environment detector.

Tests ClusterEnvironmentDetector with mocked cluster context guard.
"""

from unittest.mock import patch

import pytest

from kstack_lib.any.exceptions import KStackConfigurationError
from kstack_lib.cluster._base import ClusterBase


class TestClusterEnvironmentDetector:
    """Test ClusterEnvironmentDetector with mocked dependencies."""

    @patch.object(ClusterBase, "_check_cluster_context")
    @patch("pathlib.Path.exists", return_value=True)
    @patch("pathlib.Path.read_text", return_value="layer-3-production")
    def test_init_reads_current_namespace(self, mock_read_text, mock_exists, mock_guard):
        """Test that init reads namespace from service account."""
        from kstack_lib.cluster.config.environment import ClusterEnvironmentDetector

        detector = ClusterEnvironmentDetector()

        # Should have checked cluster context
        assert mock_guard.called
        # Should have checked file exists and read it
        assert mock_exists.called
        assert mock_read_text.called
        assert detector._namespace == "layer-3-production"

    @patch.object(ClusterBase, "_check_cluster_context")
    def test_init_with_explicit_namespace(self, mock_guard):
        """Test init with explicit namespace bypasses file read."""
        from kstack_lib.cluster.config.environment import ClusterEnvironmentDetector

        detector = ClusterEnvironmentDetector(namespace="custom-namespace")
        assert detector._namespace == "custom-namespace"

    @patch.object(ClusterBase, "_check_cluster_context")
    @patch("pathlib.Path.exists", return_value=False)
    def test_init_raises_when_namespace_file_missing(self, mock_exists, mock_guard):
        """Test that missing namespace file raises error."""
        from kstack_lib.cluster.config.environment import ClusterEnvironmentDetector

        with pytest.raises(KStackConfigurationError) as exc_info:
            ClusterEnvironmentDetector()

        assert "Cannot read namespace" in str(exc_info.value)
        assert "kubernetes.io/serviceaccount/namespace" in str(exc_info.value)

    @patch.object(ClusterBase, "_check_cluster_context")
    def test_get_environment_production(self, mock_guard):
        """Test parsing production environment."""
        from kstack_lib.cluster.config.environment import ClusterEnvironmentDetector

        detector = ClusterEnvironmentDetector(namespace="layer-3-production")
        env = detector.get_environment()

        assert env == "production"

    @patch.object(ClusterBase, "_check_cluster_context")
    def test_get_environment_staging(self, mock_guard):
        """Test parsing staging environment."""
        from kstack_lib.cluster.config.environment import ClusterEnvironmentDetector

        detector = ClusterEnvironmentDetector(namespace="layer-2-staging")
        env = detector.get_environment()

        assert env == "staging"

    @patch.object(ClusterBase, "_check_cluster_context")
    def test_get_environment_dev(self, mock_guard):
        """Test parsing dev environment."""
        from kstack_lib.cluster.config.environment import ClusterEnvironmentDetector

        detector = ClusterEnvironmentDetector(namespace="layer-1-dev")
        env = detector.get_environment()

        assert env == "dev"

    @patch.object(ClusterBase, "_check_cluster_context")
    def test_get_environment_multi_part(self, mock_guard):
        """Test parsing multi-part environment names."""
        from kstack_lib.cluster.config.environment import ClusterEnvironmentDetector

        # Environment with hyphens like "global-infra"
        detector = ClusterEnvironmentDetector(namespace="layer-3-global-infra")
        env = detector.get_environment()

        assert env == "global-infra"

    @patch.object(ClusterBase, "_check_cluster_context")
    def test_get_environment_invalid_too_short(self, mock_guard):
        """Test error when namespace format is too short."""
        from kstack_lib.cluster.config.environment import ClusterEnvironmentDetector

        detector = ClusterEnvironmentDetector(namespace="layer-3")

        with pytest.raises(KStackConfigurationError) as exc_info:
            detector.get_environment()

        assert "Invalid namespace format" in str(exc_info.value)
        assert "layer-{layer_num}-{environment}" in str(exc_info.value)
        assert "DANGEROUS" in str(exc_info.value)

    @patch.object(ClusterBase, "_check_cluster_context")
    def test_get_environment_invalid_wrong_prefix(self, mock_guard):
        """Test error when namespace doesn't start with 'layer-'."""
        from kstack_lib.cluster.config.environment import ClusterEnvironmentDetector

        detector = ClusterEnvironmentDetector(namespace="invalid-3-production")

        with pytest.raises(KStackConfigurationError) as exc_info:
            detector.get_environment()

        assert "Invalid namespace format" in str(exc_info.value)
        assert "must start with 'layer-'" in str(exc_info.value)

    @patch.object(ClusterBase, "_check_cluster_context")
    def test_get_environment_invalid_non_numeric_layer(self, mock_guard):
        """Test error when layer number is not numeric."""
        from kstack_lib.cluster.config.environment import ClusterEnvironmentDetector

        detector = ClusterEnvironmentDetector(namespace="layer-foo-production")

        with pytest.raises(KStackConfigurationError) as exc_info:
            detector.get_environment()

        assert "Invalid namespace format" in str(exc_info.value)
        assert "Layer number must be numeric" in str(exc_info.value)

    @patch.object(ClusterBase, "_check_cluster_context")
    def test_get_environment_all_layers(self, mock_guard):
        """Test that all layer numbers parse correctly."""
        from kstack_lib.cluster.config.environment import ClusterEnvironmentDetector

        for layer_num in [0, 1, 2, 3]:
            detector = ClusterEnvironmentDetector(namespace=f"layer-{layer_num}-production")
            env = detector.get_environment()
            assert env == "production"

    @patch.object(ClusterBase, "_check_cluster_context")
    def test_get_config_root_returns_none(self, mock_guard):
        """Test that config root is None in cluster."""
        from kstack_lib.cluster.config.environment import ClusterEnvironmentDetector

        detector = ClusterEnvironmentDetector(namespace="layer-3-production")
        config_root = detector.get_config_root()

        assert config_root is None

    @patch.object(ClusterBase, "_check_cluster_context")
    def test_get_vault_root_returns_none(self, mock_guard):
        """Test that vault root is None in cluster."""
        from kstack_lib.cluster.config.environment import ClusterEnvironmentDetector

        detector = ClusterEnvironmentDetector(namespace="layer-3-production")
        vault_root = detector.get_vault_root()

        assert vault_root is None

    @patch.object(ClusterBase, "_check_cluster_context")
    def test_repr_valid_namespace(self, mock_guard):
        """Test string representation with valid namespace."""
        from kstack_lib.cluster.config.environment import ClusterEnvironmentDetector

        detector = ClusterEnvironmentDetector(namespace="layer-3-production")
        repr_str = repr(detector)

        assert "ClusterEnvironmentDetector" in repr_str
        assert "layer-3-production" in repr_str
        assert "production" in repr_str

    @patch.object(ClusterBase, "_check_cluster_context")
    def test_repr_invalid_namespace(self, mock_guard):
        """Test string representation with invalid namespace."""
        from kstack_lib.cluster.config.environment import ClusterEnvironmentDetector

        detector = ClusterEnvironmentDetector(namespace="invalid")
        repr_str = repr(detector)

        # Should not raise, just show namespace
        assert "ClusterEnvironmentDetector" in repr_str
        assert "invalid" in repr_str
        assert "environment=" not in repr_str  # Can't parse environment

    @patch.object(ClusterBase, "_check_cluster_context")
    def test_whitespace_handling(self, mock_guard):
        """Test that whitespace in namespace is handled."""
        from kstack_lib.cluster.config.environment import ClusterEnvironmentDetector

        # Namespace without whitespace
        detector = ClusterEnvironmentDetector(namespace="layer-3-production")
        env = detector.get_environment()
        assert env == "production"
