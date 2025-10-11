"""
Local environment detection using .kstack.yaml (LOCAL-ONLY).

This adapter implements the EnvironmentDetector protocol for local development.
It will raise KStackEnvironmentError if imported in-cluster.
"""

from pathlib import Path

import yaml
from partsnap_logger.logging import psnap_get_logger

from kstack_lib.any.exceptions import KStackConfigurationError
from kstack_lib.local._guards import _enforce_local  # noqa: F401 - Import guard

LOGGER = psnap_get_logger("kstack_lib.local.config.environment")


class LocalEnvironmentDetector:
    """
    Detects environment from .kstack.yaml file.

    Implements the EnvironmentDetector protocol for local development.

    Example:
    -------
        ```python
        detector = LocalEnvironmentDetector()
        env = detector.get_environment()  # "dev"
        config_root = detector.get_config_root()  # Path to environments/
        vault_root = detector.get_vault_root()  # Path to vault/
        ```

    """

    def __init__(self, project_root: Path | None = None):
        """
        Initialize environment detector.

        Args:
        ----
            project_root: Optional project root (defaults to cwd)

        """
        self._project_root = project_root or Path.cwd()
        LOGGER.debug(f"Initialized local environment detector: {self._project_root}")

    def get_environment(self) -> str:
        """
        Get the active environment from .kstack.yaml.

        Returns
        -------
            Environment name (e.g., "dev", "testing", "staging")

        Raises
        ------
            KStackConfigurationError: If .kstack.yaml not found or invalid

        """
        config_file = self._find_kstack_yaml()

        if not config_file:
            raise KStackConfigurationError(
                "No .kstack.yaml found in current or parent directories.\n"
                "Create one with: echo 'environment: dev' > .kstack.yaml"
            )

        try:
            with open(config_file) as f:
                config = yaml.safe_load(f)

            if not isinstance(config, dict):
                raise KStackConfigurationError(f".kstack.yaml must contain a YAML dictionary: {config_file}")

            environment = config.get("environment")
            if not environment:
                raise KStackConfigurationError(
                    f".kstack.yaml missing 'environment' key: {config_file}\n" "Expected format: environment: dev"
                )

            LOGGER.debug(f"Detected environment '{environment}' from {config_file}")
            return environment

        except yaml.YAMLError as e:
            raise KStackConfigurationError(f"Invalid YAML in .kstack.yaml: {config_file}\n" f"Error: {e}") from e
        except Exception as e:
            raise KStackConfigurationError(f"Failed to read .kstack.yaml: {config_file}\n" f"Error: {e}") from e

    def get_config_root(self) -> Path:
        """
        Get the root path for configuration files.

        Returns
        -------
            Path to config root (environments/, providers/) or raises error

        Raises
        ------
            KStackConfigurationError: If config root not found

        """
        # Look for environments/ directory (indicator of config root)
        config_root = self._project_root / "environments"
        if config_root.exists():
            return self._project_root

        # Try parent directories
        current = self._project_root
        for _ in range(3):
            current = current.parent
            config_root = current / "environments"
            if config_root.exists():
                return current

        raise KStackConfigurationError(
            "Config root not found. Looking for 'environments/' directory.\n"
            f"Searched: {self._project_root} and parent directories"
        )

    def get_vault_root(self) -> Path:
        """
        Get the root path for vault files.

        Returns
        -------
            Path to vault root or raises error

        Raises
        ------
            KStackConfigurationError: If vault root not found

        """
        # Try current directory first
        vault_root = self._project_root / "vault"
        if vault_root.exists():
            return vault_root

        # Try parent directories
        current = self._project_root
        for _ in range(3):
            current = current.parent
            vault_root = current / "vault"
            if vault_root.exists():
                return vault_root

        raise KStackConfigurationError(
            "Vault root not found. Looking for 'vault/' directory.\n"
            f"Searched: {self._project_root} and parent directories"
        )

    def _find_kstack_yaml(self) -> Path | None:
        """
        Find .kstack.yaml in current or parent directories.

        Returns
        -------
            Path to .kstack.yaml or None if not found

        """
        # Check current directory
        config_file = self._project_root / ".kstack.yaml"
        if config_file.exists():
            return config_file

        # Check parent directories (up to 3 levels)
        current = self._project_root
        for _ in range(3):
            current = current.parent
            config_file = current / ".kstack.yaml"
            if config_file.exists():
                return config_file

        return None

    def __repr__(self) -> str:
        """Return string representation."""
        try:
            env = self.get_environment()
            return f"LocalEnvironmentDetector(environment='{env}', root='{self._project_root}')"
        except Exception:
            return f"LocalEnvironmentDetector(root='{self._project_root}')"
