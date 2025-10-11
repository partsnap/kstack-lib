"""
Vault management for partsecrets encryption (LOCAL-ONLY).

This module is LOCAL-ONLY and will raise KStackEnvironmentError if imported in-cluster.
Vaults do not exist in production - secrets come from Kubernetes Secret Manager.
"""

from collections.abc import Iterator
from pathlib import Path

from partsnap_logger.logging import psnap_get_logger

from kstack_lib.any.exceptions import KStackConfigurationError
from kstack_lib.any.utils import run_command
from kstack_lib.local._guards import _enforce_local  # noqa: F401 - Import guard

LOGGER = psnap_get_logger("kstack_lib.local.security.vault")


def get_vault_root() -> Path:
    """
    Get vault root directory.

    Returns
    -------
        Path to vault/ directory

    Raises
    ------
        KStackConfigurationError: If vault directory not found

    """
    # Try current directory first
    vault_root = Path.cwd() / "vault"
    if vault_root.exists():
        return vault_root

    # Try parent directories
    current = Path.cwd()
    for _ in range(3):
        current = current.parent
        vault_root = current / "vault"
        if vault_root.exists():
            return vault_root

    raise KStackConfigurationError(
        "Vault directory not found. Looking for 'vault/' in current or parent directories.\n"
        "Are you running from the correct project directory?"
    )


class KStackVault:
    """
    Manages partsecrets vault operations.

    A KStackVault represents an environment-specific directory containing encrypted
    secrets managed by partsecrets.

    Example:
    -------
        ```python
        # Create vault for development environment
        vault = KStackVault(environment="dev")

        # Check encryption status
        if vault.is_encrypted():
            vault.decrypt()

        # Iterate through decrypted files
        for file_path in vault.iter_decrypted_files(layer="layer3"):
            print(f"Found: {file_path}")

        # Re-encrypt when done
        vault.encrypt()
        ```

    """

    def __init__(self, environment: str, vault_root: Path | None = None):
        """
        Initialize vault for an environment.

        Args:
        ----
            environment: Environment name (dev, testing, staging, production)
            vault_root: Optional vault root path (defaults to auto-detected)

        """
        self.environment = environment
        self._vault_root = vault_root or get_vault_root()
        self.path = self._vault_root / environment

        if not self.path.exists():
            raise FileNotFoundError(
                f"Vault directory not found: {self.path}\n"
                f"Available environments: {self._list_available_environments()}"
            )

        LOGGER.debug(f"Initialized vault for environment '{environment}': {self.path}")

    def _list_available_environments(self) -> list[str]:
        """List available environments in vault."""
        if not self._vault_root.exists():
            return []
        return [p.name for p in self._vault_root.iterdir() if p.is_dir() and not p.name.startswith(".")]

    def is_encrypted(self) -> bool:
        """
        Check if vault is encrypted.

        Returns True if ANY secret.* file lacks its decrypted counterpart.
        In partsecrets, all files are encrypted/decrypted together.

        Note: Skips metadata files like secret.map.cfg which are not encrypted.
        """
        for secret_file in self.path.rglob("secret.*"):
            # Skip metadata files (partsecrets configuration)
            # secret.map.cfg tells partsecrets which files to encrypt, it's not encrypted itself
            if secret_file.suffix in {".cfg", ".conf", ".config"}:
                continue

            # Get decrypted filename by removing "secret." prefix
            decrypted_name = secret_file.name.replace("secret.", "", 1)
            decrypted_file = secret_file.parent / decrypted_name

            if not decrypted_file.exists():
                LOGGER.debug(f"Vault is encrypted: {secret_file.name} has no decrypted counterpart")
                return True

        LOGGER.debug("Vault is decrypted: all secret.* files have decrypted counterparts")
        return False

    def decrypt(self, team: str = "dev") -> bool:
        """
        Decrypt vault using partsecrets reveal.

        Args:
        ----
            team: Team name for partsecrets (default: "dev")

        Returns:
        -------
            True if successful, False otherwise

        """
        if not self.is_encrypted():
            LOGGER.info(f"Vault already decrypted: {self.path}")
            return True

        LOGGER.info(f"Decrypting vault: {self.path}")

        try:
            run_command(
                ["uv", "run", "partsecrets", "reveal", "--team", team],
                env={"PARTSECRETS_VAULT_PATH": str(self.path), "TMPDIR": "/tmp"},
                timeout=30,
            )
            LOGGER.info("✓ Vault decrypted successfully")
            return True
        except Exception as e:
            LOGGER.error(f"✗ Vault decryption failed: {e}")
            return False

    def encrypt(self, team: str = "dev") -> bool:
        """
        Encrypt vault using partsecrets hide.

        Args:
        ----
            team: Team name for partsecrets (default: "dev")

        Returns:
        -------
            True if successful, False otherwise

        """
        LOGGER.info(f"Encrypting vault: {self.path}")

        try:
            run_command(
                ["uv", "run", "partsecrets", "hide", "--team", team],
                env={"PARTSECRETS_VAULT_PATH": str(self.path), "TMPDIR": "/tmp"},
                timeout=30,
            )
            LOGGER.info("✓ Vault encrypted successfully")
            return True
        except Exception as e:
            LOGGER.error(f"✗ Vault encryption failed: {e}")
            return False

    def get_layer_path(self, layer: str) -> Path:
        """
        Get path to a specific layer directory.

        Args:
        ----
            layer: Layer identifier (e.g., "layer0", "layer3")

        Returns:
        -------
            Path to layer directory

        """
        return self.path / layer

    def get_file(self, layer: str, filename: str) -> Path:
        """
        Get path to a specific vault file.

        Args:
        ----
            layer: Layer identifier (e.g., "layer0", "layer3")
            filename: Filename (decrypted name, without "secret." prefix)

        Returns:
        -------
            Path to the file

        Example:
        -------
            ```python
            vault = KStackVault("dev")
            creds_file = vault.get_file("layer3", "cloud-credentials.yaml")
            ```

        """
        return self.path / layer / filename

    def iter_decrypted_files(self, layer: str | None = None) -> Iterator[Path]:
        """
        Iterate through all decrypted files in vault.

        Args:
        ----
            layer: Optional layer to filter by (e.g., "layer3")

        Yields:
        ------
            Path objects for each decrypted file (excludes secret.* files)

        Example:
        -------
            ```python
            vault = KStackVault("dev")
            for file in vault.iter_decrypted_files(layer="layer3"):
                print(f"Found: {file.name}")
            ```

        """
        search_path = self.get_layer_path(layer) if layer else self.path

        for file_path in search_path.rglob("*.yaml"):
            # Skip encrypted files (secret.*)
            if file_path.name.startswith("secret."):
                continue
            # Skip example/template files
            if file_path.name.endswith((".example", ".template")):
                continue

            yield file_path

    def iter_encrypted_files(self, layer: str | None = None) -> Iterator[Path]:
        """
        Iterate through all encrypted files in vault.

        Args:
        ----
            layer: Optional layer to filter by (e.g., "layer3")

        Yields:
        ------
            Path objects for each encrypted file (secret.* files)

        """
        search_path = self.get_layer_path(layer) if layer else self.path

        yield from search_path.rglob("secret.*")

    def __repr__(self) -> str:
        """Return string representation."""
        status = "encrypted" if self.is_encrypted() else "decrypted"
        return f"KStackVault(environment='{self.environment}', path='{self.path}', status='{status}')"

    def __enter__(self) -> "KStackVault":
        """Context manager entry - decrypt vault."""
        if self.is_encrypted():
            if not self.decrypt():
                raise RuntimeError(f"Failed to decrypt vault: {self.path}")
        return self

    def __exit__(self, exc_type: type[BaseException] | None, exc_val: BaseException | None, exc_tb: object) -> None:
        """Context manager exit - re-encrypt vault."""
        if not self.is_encrypted():
            self.encrypt()
