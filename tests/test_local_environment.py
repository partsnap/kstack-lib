"""Tests for LocalEnvironmentDetector."""

from unittest.mock import MagicMock, mock_open, patch

import pytest

from kstack_lib.any.exceptions import KStackConfigurationError
from kstack_lib.local.config.environment import LocalEnvironmentDetector


class TestLocalEnvironmentDetector:
    """Test LocalEnvironmentDetector."""

    @patch("kstack_lib.local.config.environment.Path")
    def test_get_environment_from_kstack_yaml(self, mock_path_cls):
        """Test reading environment from .kstack.yaml."""
        # Mock .kstack.yaml exists
        mock_yaml_file = MagicMock()
        mock_yaml_file.exists.return_value = True

        mock_cwd = MagicMock()
        mock_cwd.__truediv__ = lambda self, other: mock_yaml_file if other == ".kstack.yaml" else MagicMock()

        mock_path_cls.cwd.return_value = mock_cwd

        detector = LocalEnvironmentDetector()

        # Mock file content
        yaml_content = "environment: dev\n"
        with patch("builtins.open", mock_open(read_data=yaml_content)):
            env = detector.get_environment()
            assert env == "dev"

    @patch("kstack_lib.local.config.environment.Path")
    def test_get_environment_missing_key(self, mock_path_cls):
        """Test error when environment key is missing."""
        mock_yaml_file = MagicMock()
        mock_yaml_file.exists.return_value = True

        mock_cwd = MagicMock()
        mock_cwd.__truediv__ = lambda self, other: mock_yaml_file if other == ".kstack.yaml" else MagicMock()

        mock_path_cls.cwd.return_value = mock_cwd

        detector = LocalEnvironmentDetector()

        # Mock file with no environment key
        yaml_content = "some_other_key: value\n"
        with patch("builtins.open", mock_open(read_data=yaml_content)):
            with pytest.raises(KStackConfigurationError, match="missing 'environment' key"):
                detector.get_environment()

    @patch("kstack_lib.local.config.environment.Path")
    def test_get_environment_not_found(self, mock_path_cls):
        """Test error when .kstack.yaml not found."""
        # Mock .kstack.yaml doesn't exist anywhere
        mock_yaml_file = MagicMock()
        mock_yaml_file.exists.return_value = False

        mock_cwd = MagicMock()
        mock_cwd.__truediv__ = lambda self, other: mock_yaml_file

        # Also mock parent() to return similar structure
        mock_parent = MagicMock()
        mock_parent.__truediv__ = lambda self, other: mock_yaml_file
        mock_cwd.parent = mock_parent
        mock_parent.parent = mock_parent  # Keep returning same for all levels

        mock_path_cls.cwd.return_value = mock_cwd

        detector = LocalEnvironmentDetector()

        with pytest.raises(KStackConfigurationError, match="No .kstack.yaml found"):
            detector.get_environment()

    @patch("kstack_lib.local.config.environment.Path")
    def test_get_config_root(self, mock_path_cls):
        """Test getting config root."""
        # Mock environments/ directory exists
        mock_env_dir = MagicMock()
        mock_env_dir.exists.return_value = True

        mock_cwd = MagicMock()
        mock_cwd.__truediv__ = lambda self, other: mock_env_dir if other == "environments" else MagicMock()

        mock_path_cls.cwd.return_value = mock_cwd

        detector = LocalEnvironmentDetector()
        config_root = detector.get_config_root()

        assert config_root == mock_cwd

    @patch("kstack_lib.local.config.environment.Path")
    def test_get_config_root_not_found(self, mock_path_cls):
        """Test error when config root not found."""
        # Mock environments/ doesn't exist
        mock_env_dir = MagicMock()
        mock_env_dir.exists.return_value = False

        mock_cwd = MagicMock()
        mock_cwd.__truediv__ = lambda self, other: mock_env_dir

        # Mock parent() similar structure
        mock_parent = MagicMock()
        mock_parent.__truediv__ = lambda self, other: mock_env_dir
        mock_cwd.parent = mock_parent
        mock_parent.parent = mock_parent

        mock_path_cls.cwd.return_value = mock_cwd

        detector = LocalEnvironmentDetector()

        with pytest.raises(KStackConfigurationError, match="Config root not found"):
            detector.get_config_root()

    @patch("kstack_lib.local.config.environment.Path")
    def test_get_vault_root(self, mock_path_cls):
        """Test getting vault root."""
        # Mock vault/ directory exists
        mock_vault_dir = MagicMock()
        mock_vault_dir.exists.return_value = True

        mock_cwd = MagicMock()
        mock_cwd.__truediv__ = lambda self, other: mock_vault_dir if other == "vault" else MagicMock()

        mock_path_cls.cwd.return_value = mock_cwd

        detector = LocalEnvironmentDetector()
        vault_root = detector.get_vault_root()

        assert vault_root == mock_vault_dir

    @patch("kstack_lib.local.config.environment.Path")
    def test_get_vault_root_not_found(self, mock_path_cls):
        """Test error when vault root not found."""
        # Mock vault/ doesn't exist
        mock_vault_dir = MagicMock()
        mock_vault_dir.exists.return_value = False

        mock_cwd = MagicMock()
        mock_cwd.__truediv__ = lambda self, other: mock_vault_dir

        # Mock parent()
        mock_parent = MagicMock()
        mock_parent.__truediv__ = lambda self, other: mock_vault_dir
        mock_cwd.parent = mock_parent
        mock_parent.parent = mock_parent

        mock_path_cls.cwd.return_value = mock_cwd

        detector = LocalEnvironmentDetector()

        with pytest.raises(KStackConfigurationError, match="Vault root not found"):
            detector.get_vault_root()
