"""Tests for cluster secrets provider.

Tests ClusterSecretsProvider with mocked cluster context guard and K8s secrets.
"""

import base64
import json
import subprocess
from unittest.mock import MagicMock, mock_open, patch

import pytest

from kstack_lib.any.exceptions import KStackConfigurationError, KStackServiceNotFoundError
from kstack_lib.cluster._base import ClusterBase


class TestClusterSecretsProvider:
    """Test ClusterSecretsProvider with mocked dependencies."""

    @patch.object(ClusterBase, "_check_cluster_context")
    @patch("builtins.open", new_callable=mock_open, read_data="layer-3-production")
    def test_init_reads_current_namespace(self, mock_file, mock_guard):
        """Test that init reads namespace from service account."""
        from kstack_lib.cluster.security.secrets import ClusterSecretsProvider

        provider = ClusterSecretsProvider()

        # Should have checked cluster context
        assert mock_guard.called
        # Should have read from service account file
        mock_file.assert_called_once_with("/var/run/secrets/kubernetes.io/serviceaccount/namespace")
        assert provider._namespace == "layer-3-production"

    @patch.object(ClusterBase, "_check_cluster_context")
    def test_init_with_explicit_namespace(self, mock_guard):
        """Test init with explicit namespace bypasses file read."""
        from kstack_lib.cluster.security.secrets import ClusterSecretsProvider

        provider = ClusterSecretsProvider(namespace="my-namespace")
        assert provider._namespace == "my-namespace"

    @patch.object(ClusterBase, "_check_cluster_context")
    @patch("builtins.open", side_effect=FileNotFoundError())
    def test_init_raises_when_namespace_file_missing(self, mock_file, mock_guard):
        """Test that missing namespace file raises error."""
        from kstack_lib.cluster.security.secrets import ClusterSecretsProvider

        with pytest.raises(KStackConfigurationError) as exc_info:
            ClusterSecretsProvider()

        assert "Cannot read namespace" in str(exc_info.value)
        assert "kubernetes.io/serviceaccount/namespace" in str(exc_info.value)

    @patch.object(ClusterBase, "_check_cluster_context")
    @patch("kstack_lib.cluster.security.secrets.run_command")
    def test_get_credentials_success(self, mock_run, mock_guard):
        """Test successful credential retrieval."""
        from kstack_lib.cluster.security.secrets import ClusterSecretsProvider

        # Mock kubectl output with base64-encoded secrets
        secret_data = {
            "data": {
                "aws_access_key_id": base64.b64encode(b"AKIAEXAMPLE123").decode(),
                "aws_secret_access_key": base64.b64encode(b"secret123").decode(),
                "endpoint_url": base64.b64encode(b"http://localhost:4566").decode(),
            }
        }
        mock_run.return_value = MagicMock(stdout=json.dumps(secret_data))

        provider = ClusterSecretsProvider(namespace="layer-3-production")
        creds = provider.get_credentials("s3", "layer3", "production")

        # Verify kubectl command
        mock_run.assert_called_once()
        call_args = mock_run.call_args[0][0]
        assert call_args == [
            "kubectl",
            "get",
            "secret",
            "layer3-s3-credentials",
            "-n",
            "layer-3-production",
            "-o",
            "json",
        ]

        # Verify credentials decoded correctly
        assert creds["aws_access_key_id"] == "AKIAEXAMPLE123"
        assert creds["aws_secret_access_key"] == "secret123"
        assert creds["endpoint_url"] == "http://localhost:4566"

    @patch.object(ClusterBase, "_check_cluster_context")
    @patch("kstack_lib.cluster.security.secrets.run_command")
    def test_get_credentials_secret_not_found(self, mock_run, mock_guard):
        """Test error when K8s secret doesn't exist."""
        from kstack_lib.cluster.security.secrets import ClusterSecretsProvider

        # Mock kubectl failure with NotFound error
        error = subprocess.CalledProcessError(
            1,
            "kubectl",
            stderr='Error from server (NotFound): secrets "layer3-s3-credentials" not found',
        )
        mock_run.side_effect = error

        provider = ClusterSecretsProvider(namespace="layer-3-production")

        with pytest.raises(KStackServiceNotFoundError) as exc_info:
            provider.get_credentials("s3", "layer3", "production")

        assert "K8s secret not found" in str(exc_info.value)
        assert "layer3-s3-credentials" in str(exc_info.value)

    @patch.object(ClusterBase, "_check_cluster_context")
    @patch("kstack_lib.cluster.security.secrets.run_command")
    def test_get_credentials_kubectl_error(self, mock_run, mock_guard):
        """Test error when kubectl fails for other reasons."""
        from kstack_lib.cluster.security.secrets import ClusterSecretsProvider

        # Mock kubectl failure without NotFound
        error = subprocess.CalledProcessError(1, "kubectl", stderr="Connection refused")
        mock_run.side_effect = error

        provider = ClusterSecretsProvider(namespace="layer-3-production")

        with pytest.raises(KStackConfigurationError) as exc_info:
            provider.get_credentials("s3", "layer3", "production")

        assert "Failed to fetch K8s secret" in str(exc_info.value)

    @patch.object(ClusterBase, "_check_cluster_context")
    @patch("kstack_lib.cluster.security.secrets.run_command")
    def test_get_credentials_invalid_json(self, mock_run, mock_guard):
        """Test error when kubectl returns invalid JSON."""
        from kstack_lib.cluster.security.secrets import ClusterSecretsProvider

        mock_run.return_value = MagicMock(stdout="not valid json{")

        provider = ClusterSecretsProvider(namespace="layer-3-production")

        with pytest.raises(KStackConfigurationError) as exc_info:
            provider.get_credentials("s3", "layer3", "production")

        assert "Failed to parse K8s secret JSON" in str(exc_info.value)

    @patch.object(ClusterBase, "_check_cluster_context")
    @patch("kstack_lib.cluster.security.secrets.run_command")
    def test_get_credentials_empty_secret(self, mock_run, mock_guard):
        """Test error when secret has no data."""
        from kstack_lib.cluster.security.secrets import ClusterSecretsProvider

        secret_data = {"data": {}}
        mock_run.return_value = MagicMock(stdout=json.dumps(secret_data))

        provider = ClusterSecretsProvider(namespace="layer-3-production")

        with pytest.raises(KStackConfigurationError) as exc_info:
            provider.get_credentials("s3", "layer3", "production")

        assert "empty or malformed" in str(exc_info.value)

    @patch.object(ClusterBase, "_check_cluster_context")
    @patch("kstack_lib.cluster.security.secrets.run_command")
    def test_get_credentials_malformed_base64(self, mock_run, mock_guard):
        """Test handling of malformed base64 values."""
        from kstack_lib.cluster.security.secrets import ClusterSecretsProvider

        secret_data = {
            "data": {
                "valid_key": base64.b64encode(b"valid_value").decode(),
                "invalid_key": "not-valid-base64!!!",
            }
        }
        mock_run.return_value = MagicMock(stdout=json.dumps(secret_data))

        provider = ClusterSecretsProvider(namespace="layer-3-production")
        creds = provider.get_credentials("s3", "layer3", "production")

        # Should decode valid key, skip invalid
        assert "valid_key" in creds
        assert creds["valid_key"] == "valid_value"
        assert "invalid_key" not in creds

    @patch.object(ClusterBase, "_check_cluster_context")
    def test_repr(self, mock_guard):
        """Test string representation."""
        from kstack_lib.cluster.security.secrets import ClusterSecretsProvider

        provider = ClusterSecretsProvider(namespace="my-namespace")
        assert repr(provider) == "ClusterSecretsProvider(namespace='my-namespace')"
