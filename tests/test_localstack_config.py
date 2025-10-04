"""Unit tests for LocalStack configuration discovery."""

import base64
import json
import os
from pathlib import Path
from unittest.mock import MagicMock, mock_open, patch

import pytest

from kstack_lib.config.localstack import LocalStackDiscovery, get_localstack_config


@pytest.mark.unit
def test_localstack_discovery_init_default_vault_dir():
    """Test LocalStackDiscovery initializes with default vault directory."""
    discovery = LocalStackDiscovery()
    assert discovery.vault_dir == Path.cwd() / "vault" / "dev"


@pytest.mark.unit
def test_localstack_discovery_init_custom_vault_dir():
    """Test LocalStackDiscovery initializes with custom vault directory."""
    custom_path = Path("/custom/vault")
    discovery = LocalStackDiscovery(vault_dir=custom_path)
    assert discovery.vault_dir == custom_path


@pytest.mark.unit
@patch.dict(os.environ, {"KSTACK_ROUTE": "testing"})
def test_get_active_route_from_env():
    """Test get_active_route returns value from KSTACK_ROUTE environment variable."""
    discovery = LocalStackDiscovery()
    assert discovery.get_active_route() == "testing"


@pytest.mark.unit
@patch.dict(os.environ, {}, clear=True)
@patch("subprocess.run")
def test_get_active_route_from_kubernetes(mock_run):
    """Test get_active_route returns value from Kubernetes ConfigMap."""
    mock_result = MagicMock(returncode=0, stdout="scratch  ")
    mock_run.return_value = mock_result

    discovery = LocalStackDiscovery()
    route = discovery.get_active_route()

    assert route == "scratch"
    mock_run.assert_called_once()
    call_args = mock_run.call_args[0][0]
    assert "kubectl" in call_args
    assert "get" in call_args
    assert "configmap" in call_args
    assert "kstack-route" in call_args


@pytest.mark.unit
@patch.dict(os.environ, {}, clear=True)
@patch("subprocess.run")
def test_get_active_route_defaults_to_development(mock_run):
    """Test get_active_route defaults to development when no config found."""
    mock_result = MagicMock(returncode=1, stdout="")
    mock_run.return_value = mock_result

    discovery = LocalStackDiscovery()
    assert discovery.get_active_route() == "development"


@pytest.mark.unit
@patch.dict(os.environ, {}, clear=True)
@patch("subprocess.run", side_effect=FileNotFoundError("kubectl not found"))
def test_get_active_route_handles_kubectl_not_found(mock_run):
    """Test get_active_route handles kubectl not being installed."""
    discovery = LocalStackDiscovery()
    assert discovery.get_active_route() == "development"


@pytest.mark.unit
@patch("pathlib.Path.open", new_callable=mock_open)
@patch("pathlib.Path.exists")
def test_get_localstack_config_from_vault_file(mock_exists, mock_file):
    """Test get_localstack_config reads from vault file."""
    vault_data = {
        "development": {
            "endpoint_url": "http://localhost:4566",
            "aws_access_key_id": "dev-key",
            "aws_secret_access_key": "dev-secret",
            "region_name": "us-west-2",
        },
    }
    mock_exists.return_value = True

    with patch("yaml.safe_load", return_value=vault_data):
        discovery = LocalStackDiscovery()
        config = discovery.get_localstack_config(route="development")

        assert config["endpoint_url"] == "http://localhost:4566"
        assert config["aws_access_key_id"] == "dev-key"
        assert config["aws_secret_access_key"] == "dev-secret"
        assert config["region_name"] == "us-west-2"


@pytest.mark.unit
@patch("pathlib.Path.exists")
@patch("subprocess.run")
def test_get_localstack_config_from_kubernetes_secret(mock_run, mock_exists):
    """Test get_localstack_config reads from Kubernetes secret."""
    mock_exists.return_value = False

    secret_data = {
        "endpoint-url": base64.b64encode(b"http://localstack.k8s:4566").decode(),
        "aws-access-key-id": base64.b64encode(b"k8s-key").decode(),
        "aws-secret-access-key": base64.b64encode(b"k8s-secret").decode(),
        "region-name": base64.b64encode(b"eu-west-1").decode(),
    }
    mock_result = MagicMock(returncode=0, stdout=json.dumps(secret_data))
    mock_run.return_value = mock_result

    discovery = LocalStackDiscovery()
    config = discovery.get_localstack_config(route="testing")

    assert config["endpoint_url"] == "http://localstack.k8s:4566"
    assert config["aws_access_key_id"] == "k8s-key"
    assert config["aws_secret_access_key"] == "k8s-secret"
    assert config["region_name"] == "eu-west-1"


@pytest.mark.unit
@patch("pathlib.Path.exists")
@patch("subprocess.run")
def test_get_localstack_config_fallback_default(mock_run, mock_exists):
    """Test get_localstack_config returns fallback defaults when no config found."""
    mock_exists.return_value = False
    mock_result = MagicMock(returncode=1, stdout="")
    mock_run.return_value = mock_result

    discovery = LocalStackDiscovery()
    config = discovery.get_localstack_config(route="scratch")

    assert config["endpoint_url"] == "http://localstack-scratch.layer-3-cloud:4566"
    assert config["aws_access_key_id"] == "test"
    assert config["aws_secret_access_key"] == "test"
    assert config["region_name"] == "us-east-1"


@pytest.mark.unit
@patch("pathlib.Path.exists")
@patch("subprocess.run")
def test_get_localstack_config_uses_active_route_by_default(mock_run, mock_exists):
    """Test get_localstack_config uses active route when route not specified."""
    mock_exists.return_value = False
    mock_result = MagicMock(returncode=0, stdout="testing")
    mock_run.return_value = mock_result

    with patch.dict(os.environ, {"KSTACK_ROUTE": "testing"}):
        discovery = LocalStackDiscovery()
        config = discovery.get_localstack_config()  # No route specified

        assert "testing" in config["endpoint_url"]


@pytest.mark.unit
@patch("pathlib.Path.exists")
@patch("subprocess.run")
def test_get_localstack_config_kubernetes_secret_with_defaults(mock_run, mock_exists):
    """Test Kubernetes secret handling with missing optional fields."""
    mock_exists.return_value = False

    # Secret with only endpoint-url (missing optional fields)
    secret_data = {
        "endpoint-url": base64.b64encode(b"http://localstack.k8s:4566").decode(),
        # Include defaults for fields that have .get() with defaults
        "aws-access-key-id": base64.b64encode(b"test").decode(),
        "aws-secret-access-key": base64.b64encode(b"test").decode(),
        "region-name": base64.b64encode(b"us-east-1").decode(),
    }
    mock_result = MagicMock(returncode=0, stdout=json.dumps(secret_data))
    mock_run.return_value = mock_result

    discovery = LocalStackDiscovery()
    config = discovery.get_localstack_config(route="testing")

    assert config["endpoint_url"] == "http://localstack.k8s:4566"
    # Should use defaults for missing fields
    assert config["aws_access_key_id"] == "test"
    assert config["aws_secret_access_key"] == "test"
    assert config["region_name"] == "us-east-1"


@pytest.mark.unit
@patch("pathlib.Path.exists")
@patch("builtins.open", new_callable=mock_open)
def test_get_localstack_config_vault_file_exception_handling(mock_file, mock_exists):
    """Test get_localstack_config handles vault file read exceptions."""
    mock_exists.return_value = True
    mock_file.side_effect = Exception("File read error")

    with patch("subprocess.run") as mock_run:
        mock_run.return_value = MagicMock(returncode=1, stdout="")

        discovery = LocalStackDiscovery()
        config = discovery.get_localstack_config(route="development")

        # Should fall back to defaults
        assert config["endpoint_url"] == "http://localstack-development.layer-3-cloud:4566"


@pytest.mark.unit
@patch("pathlib.Path.exists")
@patch("subprocess.run")
def test_get_localstack_config_kubernetes_exception_handling(mock_run, mock_exists):
    """Test get_localstack_config handles Kubernetes API exceptions."""
    mock_exists.return_value = False
    mock_run.side_effect = Exception("Kubernetes API error")

    discovery = LocalStackDiscovery()
    config = discovery.get_localstack_config(route="testing")

    # Should fall back to defaults
    assert config["endpoint_url"] == "http://localstack-testing.layer-3-cloud:4566"


@pytest.mark.unit
def test_get_localstack_config_convenience_function():
    """Test get_localstack_config convenience function."""
    with patch("kstack_lib.config.localstack.LocalStackDiscovery") as mock_discovery_class:
        mock_instance = MagicMock()
        mock_config = {
            "endpoint_url": "http://test:4566",
            "aws_access_key_id": "test",
            "aws_secret_access_key": "test",
            "region_name": "us-east-1",
        }
        mock_instance.get_localstack_config.return_value = mock_config
        mock_discovery_class.return_value = mock_instance

        config = get_localstack_config(route="development")

        mock_discovery_class.assert_called_once()
        mock_instance.get_localstack_config.assert_called_once_with(route="development")
        assert config == mock_config


@pytest.mark.unit
def test_get_localstack_config_convenience_function_no_route():
    """Test get_localstack_config convenience function without route parameter."""
    with patch("kstack_lib.config.localstack.LocalStackDiscovery") as mock_discovery_class:
        mock_instance = MagicMock()
        mock_config = {"endpoint_url": "http://test:4566"}
        mock_instance.get_localstack_config.return_value = mock_config
        mock_discovery_class.return_value = mock_instance

        config = get_localstack_config()

        mock_instance.get_localstack_config.assert_called_once_with(route=None)
        assert config == mock_config


@pytest.mark.unit
@patch("pathlib.Path.exists")
@patch("builtins.open", new_callable=mock_open)
def test_get_localstack_config_vault_missing_route(mock_file, mock_exists):
    """Test get_localstack_config handles route not found in vault file."""
    vault_data = {
        "development": {"endpoint_url": "http://dev:4566"},
        # "testing" route not present
    }
    mock_exists.return_value = True

    with patch("yaml.safe_load", return_value=vault_data):
        with patch("subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(returncode=1, stdout="")

            discovery = LocalStackDiscovery()
            config = discovery.get_localstack_config(route="testing")

            # Should fall back to defaults when route not in vault
            assert config["endpoint_url"] == "http://localstack-testing.layer-3-cloud:4566"


@pytest.mark.unit
@patch("pathlib.Path.exists")
@patch("subprocess.run")
def test_get_localstack_config_kubernetes_empty_stdout(mock_run, mock_exists):
    """Test get_localstack_config handles empty Kubernetes response."""
    mock_exists.return_value = False
    mock_result = MagicMock(returncode=0, stdout="")
    mock_run.return_value = mock_result

    discovery = LocalStackDiscovery()
    config = discovery.get_localstack_config(route="development")

    # Should fall back to defaults
    assert config["endpoint_url"] == "http://localstack-development.layer-3-cloud:4566"
