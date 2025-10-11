"""Tests for KStackVault."""

from unittest.mock import patch

import pytest

from kstack_lib.any.exceptions import KStackConfigurationError
from kstack_lib.local.security.vault import KStackVault, get_vault_root


class TestGetVaultRoot:
    """Test get_vault_root function."""

    def test_finds_vault_in_current_directory(self, tmp_path, monkeypatch):
        """Test finding vault in current directory."""
        # Create vault in current directory
        vault_dir = tmp_path / "vault"
        vault_dir.mkdir()

        # Change to tmp_path
        monkeypatch.chdir(tmp_path)

        # Should find vault
        result = get_vault_root()
        assert result == vault_dir

    def test_finds_vault_in_parent_directory(self, tmp_path, monkeypatch):
        """Test finding vault in parent directory."""
        # Create vault in parent
        vault_dir = tmp_path / "vault"
        vault_dir.mkdir()

        # Create subdirectory and change to it
        subdir = tmp_path / "subdir"
        subdir.mkdir()
        monkeypatch.chdir(subdir)

        # Should find vault in parent
        result = get_vault_root()
        assert result == vault_dir

    def test_raises_if_vault_not_found(self, tmp_path, monkeypatch):
        """Test raises error if vault not found."""
        monkeypatch.chdir(tmp_path)

        with pytest.raises(KStackConfigurationError, match="Vault directory not found"):
            get_vault_root()


class TestKStackVault:
    """Test KStackVault class."""

    @pytest.fixture
    def vault_structure(self, tmp_path):
        """Create mock vault structure."""
        vault_root = tmp_path / "vault"
        vault_root.mkdir()

        # Create dev environment
        dev_env = vault_root / "dev"
        dev_env.mkdir()

        # Create layer3 directory
        layer3 = dev_env / "layer3"
        layer3.mkdir()

        # Create encrypted and decrypted files
        (layer3 / "secret.cloud-credentials.yaml").write_text("encrypted content")
        (layer3 / "cloud-credentials.yaml").write_text("aws_access_key_id: test")

        # Create layer1 directory
        layer1 = dev_env / "layer1"
        layer1.mkdir()
        (layer1 / "secret.app-config.yaml").write_text("encrypted")
        (layer1 / "app-config.yaml").write_text("config: value")

        return vault_root

    def test_init_with_valid_environment(self, vault_structure):
        """Test initializing vault with valid environment."""
        vault = KStackVault(environment="dev", vault_root=vault_structure)

        assert vault.environment == "dev"
        assert vault.path == vault_structure / "dev"
        assert vault._vault_root == vault_structure

    def test_init_with_invalid_environment(self, vault_structure):
        """Test initializing vault with invalid environment."""
        with pytest.raises(FileNotFoundError, match="Vault directory not found"):
            KStackVault(environment="nonexistent", vault_root=vault_structure)

    def test_init_without_vault_root(self, vault_structure, monkeypatch):
        """Test initializing vault without explicit vault_root."""
        monkeypatch.chdir(vault_structure.parent)

        vault = KStackVault(environment="dev")

        assert vault._vault_root == vault_structure

    def test_is_encrypted_returns_false_when_decrypted(self, vault_structure):
        """Test is_encrypted returns False when vault is decrypted."""
        vault = KStackVault(environment="dev", vault_root=vault_structure)

        assert vault.is_encrypted() is False

    def test_is_encrypted_returns_true_when_encrypted(self, vault_structure):
        """Test is_encrypted returns True when vault is encrypted."""
        vault = KStackVault(environment="dev", vault_root=vault_structure)

        # Remove decrypted file to simulate encrypted state
        (vault.path / "layer3" / "cloud-credentials.yaml").unlink()

        assert vault.is_encrypted() is True

    def test_decrypt_when_already_decrypted(self, vault_structure):
        """Test decrypt when vault is already decrypted."""
        vault = KStackVault(environment="dev", vault_root=vault_structure)

        result = vault.decrypt()

        assert result is True

    @patch("kstack_lib.local.security.vault.run_command")
    def test_decrypt_calls_partsecrets(self, mock_run_command, vault_structure):
        """Test decrypt calls partsecrets reveal command."""
        vault = KStackVault(environment="dev", vault_root=vault_structure)

        # Remove decrypted file to simulate encrypted state
        (vault.path / "layer3" / "cloud-credentials.yaml").unlink()

        vault.decrypt(team="test-team")

        mock_run_command.assert_called_once()
        args, kwargs = mock_run_command.call_args
        assert args[0] == ["uv", "run", "partsecrets", "reveal", "--team", "test-team"]
        assert kwargs["env"]["PARTSECRETS_VAULT_PATH"] == str(vault.path)

    @patch("kstack_lib.local.security.vault.run_command")
    def test_decrypt_returns_false_on_error(self, mock_run_command, vault_structure):
        """Test decrypt returns False on error."""
        vault = KStackVault(environment="dev", vault_root=vault_structure)

        # Remove decrypted file
        (vault.path / "layer3" / "cloud-credentials.yaml").unlink()

        # Make run_command raise exception
        mock_run_command.side_effect = Exception("Command failed")

        result = vault.decrypt()

        assert result is False

    @patch("kstack_lib.local.security.vault.run_command")
    def test_encrypt_calls_partsecrets(self, mock_run_command, vault_structure):
        """Test encrypt calls partsecrets hide command."""
        vault = KStackVault(environment="dev", vault_root=vault_structure)

        vault.encrypt(team="test-team")

        mock_run_command.assert_called_once()
        args, kwargs = mock_run_command.call_args
        assert args[0] == ["uv", "run", "partsecrets", "hide", "--team", "test-team"]
        assert kwargs["env"]["PARTSECRETS_VAULT_PATH"] == str(vault.path)

    @patch("kstack_lib.local.security.vault.run_command")
    def test_encrypt_returns_false_on_error(self, mock_run_command, vault_structure):
        """Test encrypt returns False on error."""
        vault = KStackVault(environment="dev", vault_root=vault_structure)

        mock_run_command.side_effect = Exception("Command failed")

        result = vault.encrypt()

        assert result is False

    def test_get_layer_path(self, vault_structure):
        """Test get_layer_path returns correct path."""
        vault = KStackVault(environment="dev", vault_root=vault_structure)

        layer_path = vault.get_layer_path("layer3")

        assert layer_path == vault.path / "layer3"

    def test_get_file(self, vault_structure):
        """Test get_file returns correct file path."""
        vault = KStackVault(environment="dev", vault_root=vault_structure)

        file_path = vault.get_file("layer3", "cloud-credentials.yaml")

        assert file_path == vault.path / "layer3" / "cloud-credentials.yaml"

    def test_iter_decrypted_files_all_layers(self, vault_structure):
        """Test iter_decrypted_files returns all decrypted files."""
        vault = KStackVault(environment="dev", vault_root=vault_structure)

        files = list(vault.iter_decrypted_files())

        # Should find 2 decrypted files (one in layer3, one in layer1)
        assert len(files) == 2
        assert any(f.name == "cloud-credentials.yaml" for f in files)
        assert any(f.name == "app-config.yaml" for f in files)

    def test_iter_decrypted_files_specific_layer(self, vault_structure):
        """Test iter_decrypted_files with layer filter."""
        vault = KStackVault(environment="dev", vault_root=vault_structure)

        files = list(vault.iter_decrypted_files(layer="layer3"))

        # Should find 1 file in layer3
        assert len(files) == 1
        assert files[0].name == "cloud-credentials.yaml"

    def test_iter_decrypted_files_skips_secret_files(self, vault_structure):
        """Test iter_decrypted_files skips secret.* files."""
        vault = KStackVault(environment="dev", vault_root=vault_structure)

        files = list(vault.iter_decrypted_files())

        # Should not include secret.* files
        assert not any(f.name.startswith("secret.") for f in files)

    def test_iter_decrypted_files_skips_templates(self, vault_structure):
        """Test iter_decrypted_files skips template files."""
        vault = KStackVault(environment="dev", vault_root=vault_structure)

        # Add template file
        (vault.path / "layer3" / "config.example").write_text("example")

        files = list(vault.iter_decrypted_files())

        # Should not include .example files
        assert not any(f.name.endswith(".example") for f in files)

    def test_iter_encrypted_files(self, vault_structure):
        """Test iter_encrypted_files returns encrypted files."""
        vault = KStackVault(environment="dev", vault_root=vault_structure)

        files = list(vault.iter_encrypted_files())

        # Should find 2 secret.* files
        assert len(files) == 2
        assert all(f.name.startswith("secret.") for f in files)

    def test_iter_encrypted_files_specific_layer(self, vault_structure):
        """Test iter_encrypted_files with layer filter."""
        vault = KStackVault(environment="dev", vault_root=vault_structure)

        files = list(vault.iter_encrypted_files(layer="layer3"))

        # Should find 1 encrypted file in layer3
        assert len(files) == 1
        assert files[0].name == "secret.cloud-credentials.yaml"

    def test_repr(self, vault_structure):
        """Test __repr__ method."""
        vault = KStackVault(environment="dev", vault_root=vault_structure)

        repr_str = repr(vault)

        assert "KStackVault" in repr_str
        assert "environment='dev'" in repr_str
        assert "decrypted" in repr_str

    @patch("kstack_lib.local.security.vault.run_command")
    def test_context_manager_decrypt_on_enter(self, mock_run_command, vault_structure):
        """Test context manager decrypts on entry if encrypted."""
        vault = KStackVault(environment="dev", vault_root=vault_structure)

        # Remove decrypted file to simulate encrypted state
        (vault.path / "layer3" / "cloud-credentials.yaml").unlink()

        with vault as v:
            assert v is vault
            mock_run_command.assert_called_once()

    @patch("kstack_lib.local.security.vault.run_command")
    def test_context_manager_encrypt_on_exit(self, mock_run_command, vault_structure):
        """Test context manager encrypts on exit if decrypted."""
        vault = KStackVault(environment="dev", vault_root=vault_structure)

        with vault:
            pass

        # Should call encrypt on exit
        mock_run_command.assert_called_once()
        args = mock_run_command.call_args[0][0]
        assert "hide" in args

    @patch("kstack_lib.local.security.vault.run_command")
    def test_context_manager_decrypt_failure_raises(self, mock_run_command, vault_structure):
        """Test context manager raises if decrypt fails."""
        vault = KStackVault(environment="dev", vault_root=vault_structure)

        # Remove decrypted file
        (vault.path / "layer3" / "cloud-credentials.yaml").unlink()

        # Make decrypt fail
        mock_run_command.side_effect = Exception("Failed")

        with pytest.raises(RuntimeError, match="Failed to decrypt vault"):
            with vault:
                pass

    def test_list_available_environments(self, vault_structure):
        """Test _list_available_environments returns environment names."""
        vault = KStackVault(environment="dev", vault_root=vault_structure)

        # Create another environment
        (vault_structure / "staging").mkdir()

        envs = vault._list_available_environments()

        assert "dev" in envs
        assert "staging" in envs
        assert len(envs) == 2

    def test_list_available_environments_empty_vault(self, tmp_path):
        """Test _list_available_environments with non-existent vault."""
        vault_root = tmp_path / "nonexistent"

        vault = KStackVault.__new__(KStackVault)
        vault._vault_root = vault_root

        envs = vault._list_available_environments()

        assert envs == []
