"""Tests for Redis configuration discovery."""

import os
import subprocess
from unittest.mock import MagicMock, patch

import pytest
import yaml

from kstack_lib.config.redis import RedisDiscovery


@pytest.fixture
def temp_vault_file(tmp_path):
    """Create a temporary vault file for testing."""
    vault_dir = tmp_path / "vault" / "dev"
    vault_dir.mkdir(parents=True)

    vault_data = {
        "development": {
            "part-raw": {
                "host": "redis-development-raw.layer-3-cloud",
                "port": 6379,
                "username": "default",
                "password": "test-password",
            },
            "part-audit": {
                "host": "redis-development-audit.layer-3-cloud",
                "port": 6379,
                "username": "default",
                "password": "test-password",
            },
        },
        "testing": {
            "part-raw": {
                "host": "redis-testing-raw.layer-3-cloud",
                "port": 6379,
                "username": "default",
                "password": "test-password",
            },
            "part-audit": {
                "host": "redis-testing-audit.layer-3-cloud",
                "port": 6379,
                "username": "default",
                "password": "test-password",
            },
        },
    }

    vault_file = vault_dir / "redis-cloud.yaml"
    with open(vault_file, "w") as f:
        yaml.dump(vault_data, f)

    return tmp_path


@pytest.mark.unit
def test_get_active_route_from_env():
    """Test route detection from environment variable."""
    with patch.dict(os.environ, {"KSTACK_ROUTE": "testing"}):
        discovery = RedisDiscovery()
        assert discovery.get_active_route() == "testing"


@pytest.mark.unit
def test_get_active_route_defaults_to_development():
    """Test route defaults to development when not specified."""
    with patch.dict(os.environ, {}, clear=True):
        with patch("subprocess.run") as mock_run:
            # Mock kubectl failure (no ConfigMap)
            mock_result = MagicMock()
            mock_result.returncode = 1
            mock_result.stdout = ""
            mock_run.return_value = mock_result

            discovery = RedisDiscovery()
            assert discovery.get_active_route() == "development"


@pytest.mark.unit
def test_get_redis_config_from_vault(temp_vault_file):
    """Test reading Redis config from vault file."""
    with patch.dict(os.environ, {"KSTACK_ROUTE": "development"}):
        # Mock the kstack_root to use our temp directory
        with patch.object(RedisDiscovery, "__init__", lambda self: None):
            discovery = RedisDiscovery()
            discovery.kstack_root = temp_vault_file
            discovery.vault_dir = temp_vault_file / "vault" / "dev"

            config = discovery.get_redis_config(database="part-raw")

            assert config["host"] == "redis-development-raw.layer-3-cloud"
            assert config["port"] == 6379
            assert config["username"] == "default"
            assert config["password"] == "test-password"


@pytest.mark.unit
def test_get_redis_config_part_audit(temp_vault_file):
    """Test reading part-audit config from vault."""
    with patch.dict(os.environ, {"KSTACK_ROUTE": "development"}):
        with patch.object(RedisDiscovery, "__init__", lambda self: None):
            discovery = RedisDiscovery()
            discovery.kstack_root = temp_vault_file
            discovery.vault_dir = temp_vault_file / "vault" / "dev"

            config = discovery.get_redis_config(database="part-audit")

            assert config["host"] == "redis-development-audit.layer-3-cloud"
            assert config["port"] == 6379


@pytest.mark.unit
def test_get_redis_config_missing_route_raises_error(temp_vault_file):
    """Test that missing route configuration raises ServiceNotFoundError."""
    from kstack_lib.exceptions import ServiceNotFoundError

    with patch.dict(os.environ, {"KSTACK_ROUTE": "nonexistent"}):
        with patch.object(RedisDiscovery, "__init__", lambda self: None):
            discovery = RedisDiscovery()
            discovery.kstack_root = temp_vault_file
            discovery.vault_dir = temp_vault_file / "vault" / "dev"

            with pytest.raises(ServiceNotFoundError, match="Redis configuration not found"):
                discovery.get_redis_config(database="part-raw")


@pytest.mark.unit
def test_get_redis_config_missing_database_raises_error(temp_vault_file):
    """Test that missing database configuration raises ServiceNotFoundError."""
    from kstack_lib.exceptions import ServiceNotFoundError

    with patch.dict(os.environ, {"KSTACK_ROUTE": "development"}):
        with patch.object(RedisDiscovery, "__init__", lambda self: None):
            discovery = RedisDiscovery()
            discovery.kstack_root = temp_vault_file
            discovery.vault_dir = temp_vault_file / "vault" / "dev"

            # Remove part-audit from vault data
            vault_file = temp_vault_file / "vault" / "dev" / "redis-cloud.yaml"
            with open(vault_file) as f:
                vault_data = yaml.safe_load(f)

            del vault_data["development"]["part-audit"]

            with open(vault_file, "w") as f:
                yaml.dump(vault_data, f)

            # Mock subprocess.run to prevent fallback to real K8s cluster
            with patch("subprocess.run") as mock_run:
                # Make kubectl calls fail
                mock_run.side_effect = subprocess.CalledProcessError(1, ["kubectl"])

                with pytest.raises(ServiceNotFoundError, match="Redis configuration not found"):
                    discovery.get_redis_config(database="part-audit")


@pytest.mark.unit
@patch("subprocess.run")
@patch.dict(os.environ, {}, clear=True)
def test_get_active_route_from_kubernetes_configmap(mock_run):
    """Test route detection from Kubernetes ConfigMap."""
    mock_result = MagicMock(returncode=0, stdout="scratch  ")
    mock_run.return_value = mock_result

    discovery = RedisDiscovery()
    route = discovery.get_active_route()

    assert route == "scratch"
    # Verify kubectl was called
    mock_run.assert_called_once()


@pytest.mark.unit
@patch("subprocess.run", side_effect=FileNotFoundError("kubectl not found"))
@patch.dict(os.environ, {}, clear=True)
def test_get_active_route_handles_kubectl_not_found(mock_run):
    """Test route defaults when kubectl is not installed."""
    discovery = RedisDiscovery()
    assert discovery.get_active_route() == "development"


@pytest.mark.unit
@patch("subprocess.run")
@patch("pathlib.Path.exists", return_value=False)
@patch.dict(os.environ, {"KSTACK_ROUTE": "testing"})
def test_get_redis_config_from_kubernetes_secret(mock_exists, mock_run):
    """Test reading Redis config from Kubernetes secret."""
    import base64

    # Mock successful kubectl calls for each field
    def kubectl_side_effect(*args, **kwargs):
        command = " ".join(args[0])
        result = MagicMock(returncode=0)

        if "redis-host" in command:
            result.stdout = base64.b64encode(b"redis-k8s.local").decode() + " "
        elif "redis-port" in command:
            result.stdout = base64.b64encode(b"6380").decode() + " "
        elif "redis-username" in command:
            result.stdout = base64.b64encode(b"k8s-user").decode() + " "
        elif "redis-password" in command:
            result.stdout = base64.b64encode(b"k8s-password").decode() + " "
        else:
            result.stdout = ""

        return result

    mock_run.side_effect = kubectl_side_effect

    discovery = RedisDiscovery()
    config = discovery.get_redis_config(database="part-raw")

    assert config["host"] == "redis-k8s.local"
    assert config["port"] == 6380
    assert config["username"] == "k8s-user"
    assert config["password"] == "k8s-password"


@pytest.mark.unit
@patch("subprocess.run")
@patch("pathlib.Path.exists", return_value=False)
@patch.dict(os.environ, {"KSTACK_ROUTE": "testing"})
def test_get_redis_config_from_kubernetes_secret_audit(mock_exists, mock_run):
    """Test reading part-audit config from Kubernetes secret uses correct prefix."""
    import base64

    # Mock successful kubectl calls
    def kubectl_side_effect(*args, **kwargs):
        command = " ".join(args[0])
        result = MagicMock(returncode=0)

        # Check for audit- prefix
        if "audit-redis-host" in command:
            result.stdout = base64.b64encode(b"redis-audit.local").decode() + " "
        elif "audit-redis-port" in command:
            result.stdout = base64.b64encode(b"6381").decode() + " "
        elif "audit-redis-username" in command:
            result.stdout = base64.b64encode(b"audit-user").decode() + " "
        elif "audit-redis-password" in command:
            result.stdout = base64.b64encode(b"audit-pass").decode() + " "
        else:
            result.stdout = ""

        return result

    mock_run.side_effect = kubectl_side_effect

    discovery = RedisDiscovery()
    config = discovery.get_redis_config(database="part-audit")

    assert config["host"] == "redis-audit.local"
    assert config["port"] == 6381
    assert config["username"] == "audit-user"
    assert config["password"] == "audit-pass"


@pytest.mark.unit
@patch("subprocess.run", side_effect=subprocess.CalledProcessError(1, ["kubectl"]))
@patch("pathlib.Path.exists", return_value=False)
@patch.dict(os.environ, {"KSTACK_ROUTE": "testing"})
def test_get_redis_config_raises_on_all_failures(mock_exists, mock_run):
    """Test that ServiceNotFoundError is raised when all config sources fail."""
    from kstack_lib.exceptions import ServiceNotFoundError

    discovery = RedisDiscovery()

    with pytest.raises(ServiceNotFoundError, match="Redis configuration not found"):
        discovery.get_redis_config(database="part-raw")


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
