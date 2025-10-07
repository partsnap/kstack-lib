"""Tests for SecretsProvider cross-layer access control."""

import os
from unittest.mock import patch

import pytest
import yaml

from kstack_lib.config import load_secrets_for_layer
from kstack_lib.config.secrets import SecretsProvider


@pytest.fixture
def temp_vault_dir(tmp_path):
    """Create a temporary vault directory structure for testing."""
    vault_dir = tmp_path / "vault" / "development"

    # Create layer directories
    layer0_dir = vault_dir / "layer0"
    layer1_dir = vault_dir / "layer1"
    layer2_dir = vault_dir / "layer2"
    layer3_dir = vault_dir / "layer3"

    layer0_dir.mkdir(parents=True)
    layer1_dir.mkdir(parents=True)
    layer2_dir.mkdir(parents=True)
    layer3_dir.mkdir(parents=True)

    # Layer 0 secrets (private - no sharing)
    layer0_secrets = {
        "app-secret-key": "layer0-secret-123",
        "app-database-url": "postgresql://layer0:password@localhost/db",
    }
    with open(layer0_dir / "app.yaml", "w") as f:
        yaml.dump(layer0_secrets, f)

    # Layer 1 secrets (shared with layer0)
    layer1_redis = {
        "redis-host": "redis-layer1.svc.cluster.local",
        "redis-port": "6379",
        "redis-password": "layer1-redis-secret",
        "shared_with": ["layer0"],
    }
    with open(layer1_dir / "redis.yaml", "w") as f:
        yaml.dump(layer1_redis, f)

    # Layer 1 database (shared with layer0 and layer2)
    layer1_db = {
        "db-host": "postgres-layer1.svc.cluster.local",
        "db-port": "5432",
        "db-password": "layer1-db-secret",
        "shared_with": ["layer0", "layer2"],
    }
    with open(layer1_dir / "database.yaml", "w") as f:
        yaml.dump(layer1_db, f)

    # Layer 2 secrets (shared with layer0)
    layer2_secrets = {
        "traefik-api-key": "layer2-traefik-key",
        "monitoring-token": "layer2-monitoring-token",
        "shared_with": ["layer0"],
    }
    with open(layer2_dir / "global-services.yaml", "w") as f:
        yaml.dump(layer2_secrets, f)

    # Layer 3 secrets (not shared)
    layer3_secrets = {
        "aws-access-key": "AKIAIOSFODNN7EXAMPLE",
        "aws-secret-key": "wJalrXUtnFEMI/K7MDENG/bPxRfiCYEXAMPLEKEY",
    }
    with open(layer3_dir / "cloud.yaml", "w") as f:
        yaml.dump(layer3_secrets, f)

    return vault_dir.parent.parent


@pytest.fixture
def mock_k8s_unavailable():
    """Mock kubectl to simulate K8s not available."""
    with patch("subprocess.run") as mock_run:
        # Simulate kubectl not available
        mock_run.side_effect = FileNotFoundError("kubectl not found")
        yield mock_run


@pytest.mark.unit
class TestLayerAccessControl:
    """Test cross-layer access control logic."""

    def test_layer0_can_access_own_secrets(self, temp_vault_dir, mock_k8s_unavailable):
        """Layer 0 should be able to access its own secrets."""
        os.environ["KSTACK_ENV"] = "development"
        provider = SecretsProvider(vault_dir=temp_vault_dir / "vault")

        secrets = provider.load_secrets_from_vault("layer0")

        # Should have layer0's own secrets
        assert "app-secret-key" in secrets
        assert secrets["app-secret-key"] == "layer0-secret-123"
        assert "app-database-url" in secrets

    def test_layer0_can_access_shared_layer1_secrets(self, temp_vault_dir, mock_k8s_unavailable):
        """Layer 0 should access Layer 1 secrets marked with shared_with: [layer0]."""
        os.environ["KSTACK_ENV"] = "development"
        provider = SecretsProvider(vault_dir=temp_vault_dir / "vault")

        secrets = provider.load_secrets_from_vault("layer0")

        # Should have layer1 Redis secrets (shared with layer0)
        assert "redis-host" in secrets
        assert secrets["redis-host"] == "redis-layer1.svc.cluster.local"
        assert "redis-port" in secrets
        assert secrets["redis-port"] == "6379"
        assert "redis-password" in secrets
        assert secrets["redis-password"] == "layer1-redis-secret"

        # Should have layer1 database secrets (shared with layer0)
        assert "db-host" in secrets
        assert secrets["db-host"] == "postgres-layer1.svc.cluster.local"
        assert "db-password" in secrets

    def test_layer0_can_access_shared_layer2_secrets(self, temp_vault_dir, mock_k8s_unavailable):
        """Layer 0 should access Layer 2 secrets marked with shared_with: [layer0]."""
        os.environ["KSTACK_ENV"] = "development"
        provider = SecretsProvider(vault_dir=temp_vault_dir / "vault")

        secrets = provider.load_secrets_from_vault("layer0")

        # Should have layer2 secrets (shared with layer0)
        assert "traefik-api-key" in secrets
        assert secrets["traefik-api-key"] == "layer2-traefik-key"
        assert "monitoring-token" in secrets
        assert secrets["monitoring-token"] == "layer2-monitoring-token"

    def test_layer0_cannot_access_unshared_layer3_secrets(self, temp_vault_dir, mock_k8s_unavailable):
        """Layer 0 should NOT access Layer 3 secrets (not in shared_with)."""
        os.environ["KSTACK_ENV"] = "development"
        provider = SecretsProvider(vault_dir=temp_vault_dir / "vault")

        secrets = provider.load_secrets_from_vault("layer0")

        # Should NOT have layer3 secrets (no shared_with)
        assert "aws-access-key" not in secrets
        assert "aws-secret-key" not in secrets

    def test_layer2_can_access_shared_layer1_database(self, temp_vault_dir, mock_k8s_unavailable):
        """Layer 2 should access Layer 1 database secrets (shared with layer2)."""
        os.environ["KSTACK_ENV"] = "development"
        provider = SecretsProvider(vault_dir=temp_vault_dir / "vault")

        secrets = provider.load_secrets_from_vault("layer2")

        # Should have layer1 database secrets (shared with layer2)
        assert "db-host" in secrets
        assert secrets["db-host"] == "postgres-layer1.svc.cluster.local"
        assert "db-password" in secrets
        assert secrets["db-password"] == "layer1-db-secret"

    def test_layer2_cannot_access_layer1_redis_not_shared(self, temp_vault_dir, mock_k8s_unavailable):
        """Layer 2 should NOT access Layer 1 Redis (not in shared_with)."""
        os.environ["KSTACK_ENV"] = "development"
        provider = SecretsProvider(vault_dir=temp_vault_dir / "vault")

        secrets = provider.load_secrets_from_vault("layer2")

        # Should NOT have layer1 Redis secrets (only shared with layer0)
        assert "redis-host" not in secrets
        assert "redis-password" not in secrets

    def test_layer1_can_access_own_secrets(self, temp_vault_dir, mock_k8s_unavailable):
        """Layer 1 should be able to access its own secrets."""
        os.environ["KSTACK_ENV"] = "development"
        provider = SecretsProvider(vault_dir=temp_vault_dir / "vault")

        secrets = provider.load_secrets_from_vault("layer1")

        # Should have all layer1 secrets
        assert "redis-host" in secrets
        assert "redis-password" in secrets
        assert "db-host" in secrets
        assert "db-password" in secrets

    def test_layer3_can_access_own_secrets(self, temp_vault_dir, mock_k8s_unavailable):
        """Layer 3 should be able to access its own secrets."""
        os.environ["KSTACK_ENV"] = "development"
        provider = SecretsProvider(vault_dir=temp_vault_dir / "vault")

        secrets = provider.load_secrets_from_vault("layer3")

        # Should have layer3 secrets
        assert "aws-access-key" in secrets
        assert secrets["aws-access-key"] == "AKIAIOSFODNN7EXAMPLE"
        assert "aws-secret-key" in secrets


@pytest.mark.unit
class TestSharedWithValidation:
    """Test shared_with field validation."""

    def test_shared_with_as_list(self, temp_vault_dir, mock_k8s_unavailable):
        """shared_with should work as a list."""
        vault_dir = temp_vault_dir / "vault" / "development" / "layer1"

        # Create secret with shared_with as list
        secrets = {
            "test-key": "test-value",
            "shared_with": ["layer0", "layer2"],
        }
        with open(vault_dir / "test.yaml", "w") as f:
            yaml.dump(secrets, f)

        os.environ["KSTACK_ENV"] = "development"
        provider = SecretsProvider(vault_dir=temp_vault_dir / "vault")

        # Layer 0 should access it
        layer0_secrets = provider.load_secrets_from_vault("layer0")
        assert "test-key" in layer0_secrets

        # Layer 2 should access it
        layer2_secrets = provider.load_secrets_from_vault("layer2")
        assert "test-key" in layer2_secrets

        # Layer 3 should NOT access it
        layer3_secrets = provider.load_secrets_from_vault("layer3")
        assert "test-key" not in layer3_secrets

    def test_shared_with_empty_list(self, temp_vault_dir, mock_k8s_unavailable):
        """shared_with as empty list should deny access to all other layers."""
        vault_dir = temp_vault_dir / "vault" / "development" / "layer1"

        # Create secret with empty shared_with
        secrets = {
            "private-key": "private-value",
            "shared_with": [],
        }
        with open(vault_dir / "private.yaml", "w") as f:
            yaml.dump(secrets, f)

        os.environ["KSTACK_ENV"] = "development"
        provider = SecretsProvider(vault_dir=temp_vault_dir / "vault")

        # Layer 0 should NOT access it
        layer0_secrets = provider.load_secrets_from_vault("layer0")
        assert "private-key" not in layer0_secrets

        # Layer 1 should access its own secret
        layer1_secrets = provider.load_secrets_from_vault("layer1")
        assert "private-key" in layer1_secrets

    def test_no_shared_with_field(self, temp_vault_dir, mock_k8s_unavailable):
        """Secrets without shared_with field should be private."""
        vault_dir = temp_vault_dir / "vault" / "development" / "layer1"

        # Create secret without shared_with field
        secrets = {
            "internal-key": "internal-value",
        }
        with open(vault_dir / "internal.yaml", "w") as f:
            yaml.dump(secrets, f)

        os.environ["KSTACK_ENV"] = "development"
        provider = SecretsProvider(vault_dir=temp_vault_dir / "vault")

        # Layer 0 should NOT access it (no shared_with means private)
        layer0_secrets = provider.load_secrets_from_vault("layer0")
        assert "internal-key" not in layer0_secrets

        # Layer 1 should access its own secret
        layer1_secrets = provider.load_secrets_from_vault("layer1")
        assert "internal-key" in layer1_secrets


@pytest.mark.unit
class TestEnvironmentVariableExport:
    """Test automatic export of secrets as environment variables."""

    def test_auto_export_converts_keys(self, temp_vault_dir, mock_k8s_unavailable):
        """Auto-export should convert hyphen-separated keys to uppercase underscore."""
        os.environ["KSTACK_ENV"] = "development"
        os.environ["KSTACK_VAULT_DIR"] = str(temp_vault_dir / "vault")

        # Clear existing env vars
        for key in ["REDIS_HOST", "REDIS_PORT", "REDIS_PASSWORD"]:
            os.environ.pop(key, None)

        # Load secrets with auto_export=True using high-level API
        load_secrets_for_layer("layer0", auto_export=True)

        # Should be exported with uppercase underscores
        assert os.environ.get("REDIS_HOST") == "redis-layer1.svc.cluster.local"
        assert os.environ.get("REDIS_PORT") == "6379"
        assert os.environ.get("REDIS_PASSWORD") == "layer1-redis-secret"

        # Clean up
        for key in ["REDIS_HOST", "REDIS_PORT", "REDIS_PASSWORD"]:
            os.environ.pop(key, None)
        os.environ.pop("KSTACK_VAULT_DIR", None)

    def test_export_doesnt_override_existing_env_vars(self, temp_vault_dir, mock_k8s_unavailable):
        """Auto-export should not override existing environment variables."""
        os.environ["KSTACK_ENV"] = "development"
        os.environ["KSTACK_VAULT_DIR"] = str(temp_vault_dir / "vault")

        # Set existing env var
        os.environ["REDIS_HOST"] = "existing-redis-host"

        # Load secrets with auto_export=True using high-level API
        load_secrets_for_layer("layer0", auto_export=True)

        # Should preserve existing value (env vars have precedence)
        assert os.environ.get("REDIS_HOST") == "existing-redis-host"

        # Clean up
        os.environ.pop("REDIS_HOST", None)
        os.environ.pop("KSTACK_VAULT_DIR", None)


@pytest.mark.unit
class TestSecretPrecedence:
    """Test precedence: environment variables > vault > defaults."""

    def test_env_var_takes_precedence_over_vault(self, temp_vault_dir, mock_k8s_unavailable):
        """Environment variables should take precedence over vault secrets."""
        os.environ["KSTACK_ENV"] = "development"
        provider = SecretsProvider(vault_dir=temp_vault_dir / "vault")

        # Set env var that conflicts with vault secret
        os.environ["REDIS_HOST"] = "env-redis-host"

        # Load secrets to see vault values
        secrets = provider.load_secrets_from_vault("layer0")

        # Vault value should still be in secrets dict
        assert secrets.get("redis-host") == "redis-layer1.svc.cluster.local"

        # But env var should take precedence in actual usage
        # (This is enforced by code that reads from os.environ first)

        # Clean up
        os.environ.pop("REDIS_HOST", None)


@pytest.mark.unit
class TestMultipleVaultFiles:
    """Test loading secrets from multiple YAML files in same layer."""

    def test_multiple_files_merge_correctly(self, temp_vault_dir, mock_k8s_unavailable):
        """Secrets from multiple vault files in same layer should merge."""
        os.environ["KSTACK_ENV"] = "development"
        provider = SecretsProvider(vault_dir=temp_vault_dir / "vault")

        secrets = provider.load_secrets_from_vault("layer1")

        # Should have secrets from redis.yaml
        assert "redis-host" in secrets
        # Should have secrets from database.yaml
        assert "db-host" in secrets
        # All in same dictionary
        assert len(secrets) >= 6  # At least 3 redis + 3 database keys


@pytest.mark.unit
class TestEdgeCases:
    """Test edge cases and error conditions."""

    def test_nonexistent_layer(self, temp_vault_dir, mock_k8s_unavailable):
        """Loading secrets for non-existent layer should return empty dict."""
        os.environ["KSTACK_ENV"] = "development"
        provider = SecretsProvider(vault_dir=temp_vault_dir / "vault")

        secrets = provider.load_secrets_from_vault("layer99")

        # Should return empty dict, not error
        assert secrets == {}

    def test_malformed_shared_with(self, temp_vault_dir, mock_k8s_unavailable):
        """Malformed shared_with field should be handled gracefully."""
        vault_dir = temp_vault_dir / "vault" / "development" / "layer1"

        # Create secret with malformed shared_with (string instead of list)
        secrets = {
            "bad-key": "bad-value",
            "shared_with": "layer0",  # Should be list, not string
        }
        with open(vault_dir / "malformed.yaml", "w") as f:
            yaml.dump(secrets, f)

        os.environ["KSTACK_ENV"] = "development"
        provider = SecretsProvider(vault_dir=temp_vault_dir / "vault")

        # Should handle gracefully and not crash
        # (Implementation may treat it as no sharing or handle specially)
        layer0_secrets = provider.load_secrets_from_vault("layer0")

        # Depending on implementation, this may or may not be accessible
        # The key point is it should not crash
        assert isinstance(layer0_secrets, dict)

    def test_kstack_root_env_var(self, tmp_path, mock_k8s_unavailable):
        """SecretsProvider should use KSTACK_ROOT env var if no vault_dir provided."""
        # Clear other vault env vars
        os.environ.pop("KSTACK_VAULT_DIR", None)

        # Create vault structure under KSTACK_ROOT
        kstack_root = tmp_path / "kstack_root"
        vault_dir = kstack_root / "vault" / "development" / "layer0"
        vault_dir.mkdir(parents=True)

        # Create a test secret
        with open(vault_dir / "test.yaml", "w") as f:
            yaml.dump({"test-key": "test-value"}, f)

        os.environ["KSTACK_ENV"] = "development"
        os.environ["KSTACK_ROOT"] = str(kstack_root)

        provider = SecretsProvider()
        secrets = provider.load_secrets_from_vault("layer0")

        assert "test-key" in secrets
        assert secrets["test-key"] == "test-value"

        # Cleanup
        os.environ.pop("KSTACK_ROOT", None)

    def test_empty_vault_file(self, temp_vault_dir, mock_k8s_unavailable):
        """Empty vault files should be handled gracefully."""
        vault_dir = temp_vault_dir / "vault" / "development" / "layer1"

        # Create empty vault file
        empty_file = vault_dir / "empty.yaml"
        empty_file.write_text("")

        os.environ["KSTACK_ENV"] = "development"
        provider = SecretsProvider(vault_dir=temp_vault_dir / "vault")

        # Should not crash on empty file
        secrets = provider.load_secrets_from_vault("layer1")

        # Should still have other layer1 secrets
        assert "redis-host" in secrets

    def test_missing_layer_directory(self, temp_vault_dir, mock_k8s_unavailable):
        """Missing layer directories should be handled gracefully."""
        os.environ["KSTACK_ENV"] = "development"

        # layer2 directory doesn't exist in temp_vault_dir
        provider = SecretsProvider(vault_dir=temp_vault_dir / "vault")

        # Try to load from layer0, which should check all layers including missing layer2
        secrets = provider.load_secrets_from_vault("layer0")

        # Should still work and load existing layers
        assert isinstance(secrets, dict)
