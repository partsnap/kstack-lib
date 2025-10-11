"""Tests for LocalCredentialsProvider."""

from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from kstack_lib.any.exceptions import KStackConfigurationError, KStackServiceNotFoundError
from kstack_lib.local.security.credentials import LocalCredentialsProvider
from kstack_lib.local.security.vault import KStackVault


class TestLocalCredentialsProvider:
    """Test LocalCredentialsProvider class."""

    @pytest.fixture
    def mock_vault(self, tmp_path):
        """Create a mock vault with test structure."""
        vault_root = tmp_path / "vault"
        vault_root.mkdir()

        dev_env = vault_root / "dev"
        dev_env.mkdir()

        layer3 = dev_env / "layer3"
        layer3.mkdir()

        # Create mock vault instance
        vault = MagicMock(spec=KStackVault)
        vault.environment = "dev"
        vault.path = dev_env
        vault._vault_root = vault_root
        vault.is_encrypted.return_value = False

        return vault

    @pytest.fixture
    def credentials_file(self, tmp_path):
        """Create a mock credentials file."""
        vault_root = tmp_path / "vault"
        vault_root.mkdir(exist_ok=True)

        dev_env = vault_root / "dev"
        dev_env.mkdir(exist_ok=True)

        layer3 = dev_env / "layer3"
        layer3.mkdir(exist_ok=True)

        creds_file = layer3 / "cloud-credentials.yaml"
        creds_file.write_text("""
s3:
  aws_access_key_id: test-access-key
  aws_secret_access_key: test-secret-key
  endpoint_url: http://localhost:4566
  region: us-east-1

redis:
  host: localhost
  port: 6379
  password: test-password
""")
        return vault_root

    def test_init_with_vault_instance(self, mock_vault):
        """Test initialization with vault instance."""
        provider = LocalCredentialsProvider(vault=mock_vault)

        assert provider._vault == mock_vault

    def test_init_with_environment_string(self):
        """Test initialization with environment string."""
        with patch("kstack_lib.local.security.credentials.KStackVault") as mock_vault_class:
            mock_vault_instance = MagicMock()
            mock_vault_class.return_value = mock_vault_instance

            provider = LocalCredentialsProvider(environment="dev")

            mock_vault_class.assert_called_once_with(environment="dev")
            assert provider._vault == mock_vault_instance

    def test_init_without_vault_or_environment_raises(self):
        """Test initialization without vault or environment raises ValueError."""
        with pytest.raises(ValueError, match="Either vault or environment must be provided"):
            LocalCredentialsProvider()

    def test_get_credentials_success(self, mock_vault, credentials_file):
        """Test successful credentials retrieval."""
        vault = KStackVault(environment="dev", vault_root=credentials_file)
        provider = LocalCredentialsProvider(vault=vault)

        creds = provider.get_credentials("s3", "layer3", "dev")

        assert creds["aws_access_key_id"] == "test-access-key"
        assert creds["aws_secret_access_key"] == "test-secret-key"
        assert creds["endpoint_url"] == "http://localhost:4566"
        assert creds["region"] == "us-east-1"

    def test_get_credentials_different_service(self, credentials_file):
        """Test retrieving credentials for different service."""
        vault = KStackVault(environment="dev", vault_root=credentials_file)
        provider = LocalCredentialsProvider(vault=vault)

        creds = provider.get_credentials("redis", "layer3", "dev")

        assert creds["host"] == "localhost"
        assert creds["port"] == 6379
        assert creds["password"] == "test-password"

    def test_get_credentials_environment_mismatch_raises(self, mock_vault):
        """Test environment mismatch raises KStackConfigurationError."""
        mock_vault.environment = "dev"
        provider = LocalCredentialsProvider(vault=mock_vault)

        with pytest.raises(
            KStackConfigurationError,
            match="Vault environment mismatch: vault is 'dev', requested 'staging'",
        ):
            provider.get_credentials("s3", "layer3", "staging")

    def test_get_credentials_auto_decrypts_vault(self, mock_vault, credentials_file):
        """Test auto-decryption of encrypted vault."""
        # Create real vault but mock the decrypt behavior
        vault = KStackVault(environment="dev", vault_root=credentials_file)
        provider = LocalCredentialsProvider(vault=vault)

        # Mock is_encrypted to return True, then False after decrypt
        with patch.object(vault, "is_encrypted", side_effect=[True, False]):
            with patch.object(vault, "decrypt", return_value=True) as mock_decrypt:
                creds = provider.get_credentials("s3", "layer3", "dev")

                mock_decrypt.assert_called_once()
                assert creds["aws_access_key_id"] == "test-access-key"

    def test_get_credentials_decrypt_failure_raises(self, mock_vault):
        """Test decrypt failure raises KStackConfigurationError."""
        mock_vault.is_encrypted.return_value = True
        mock_vault.decrypt.return_value = False
        mock_vault.path = Path("/fake/path")

        provider = LocalCredentialsProvider(vault=mock_vault)

        with pytest.raises(
            KStackConfigurationError,
            match=r"Failed to decrypt vault",
        ):
            provider.get_credentials("s3", "layer3", "dev")

    def test_get_credentials_file_not_found_raises(self, mock_vault, tmp_path):
        """Test missing credentials file raises KStackServiceNotFoundError."""
        # Setup vault with no credentials file
        dev_env = tmp_path / "dev"
        dev_env.mkdir()
        layer3 = dev_env / "layer3"
        layer3.mkdir()

        mock_vault.environment = "dev"
        mock_vault.path = dev_env
        mock_vault.is_encrypted.return_value = False
        mock_vault.get_file.return_value = dev_env / "layer3" / "cloud-credentials.yaml"

        provider = LocalCredentialsProvider(vault=mock_vault)

        with pytest.raises(
            KStackServiceNotFoundError,
            match=r"Credentials file not found",
        ):
            provider.get_credentials("s3", "layer3", "dev")

    def test_get_credentials_malformed_yaml_raises(self, mock_vault, tmp_path):
        """Test malformed YAML raises KStackConfigurationError."""
        # Create file with invalid YAML
        dev_env = tmp_path / "dev"
        dev_env.mkdir()
        layer3 = dev_env / "layer3"
        layer3.mkdir()

        creds_file = layer3 / "cloud-credentials.yaml"
        creds_file.write_text("{ invalid yaml content [")

        mock_vault.environment = "dev"
        mock_vault.path = dev_env
        mock_vault.is_encrypted.return_value = False
        mock_vault.get_file.return_value = creds_file

        provider = LocalCredentialsProvider(vault=mock_vault)

        with pytest.raises(
            KStackConfigurationError,
            match="Failed to parse credentials file",
        ):
            provider.get_credentials("s3", "layer3", "dev")

    def test_get_credentials_service_not_found_raises(self, credentials_file):
        """Test requesting non-existent service raises KStackServiceNotFoundError."""
        vault = KStackVault(environment="dev", vault_root=credentials_file)
        provider = LocalCredentialsProvider(vault=vault)

        with pytest.raises(
            KStackServiceNotFoundError,
            match=r"Service 'postgres' not found in credentials file",
        ):
            provider.get_credentials("postgres", "layer3", "dev")

    def test_get_credentials_file_read_error_raises(self, mock_vault, tmp_path):
        """Test file read error raises KStackConfigurationError."""
        # Create credentials file
        dev_env = tmp_path / "dev"
        dev_env.mkdir()
        layer3 = dev_env / "layer3"
        layer3.mkdir()

        creds_file = layer3 / "cloud-credentials.yaml"
        creds_file.write_text("s3:\n  key: value")

        mock_vault.environment = "dev"
        mock_vault.path = dev_env
        mock_vault.is_encrypted.return_value = False
        mock_vault.get_file.return_value = creds_file

        provider = LocalCredentialsProvider(vault=mock_vault)

        # Mock open to raise an exception
        with patch("builtins.open", side_effect=PermissionError("Permission denied")):
            with pytest.raises(
                KStackConfigurationError,
                match=r"Failed to parse credentials file",
            ):
                provider.get_credentials("s3", "layer3", "dev")

    def test_repr(self, mock_vault):
        """Test __repr__ method."""
        provider = LocalCredentialsProvider(vault=mock_vault)

        repr_str = repr(provider)

        assert "LocalCredentialsProvider" in repr_str
        assert "vault=" in repr_str
