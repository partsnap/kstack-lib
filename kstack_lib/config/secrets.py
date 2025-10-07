"""
Unified secrets management for KStack.

Automatically discovers secrets from vault (runmode) or K8s secrets (deployed mode).
Supports layer-based access control and cross-layer secret sharing.

Example:
-------
    from kstack_lib.config import load_secrets_for_layer

    # Load all accessible secrets for layer 0 and export as env vars
    load_secrets_for_layer(layer="layer0", auto_export=True)

    # Now environment variables are set and libraries like partsnap-rediscache can use them
    from partsnap_rediscache.config import RedisConfig
    config = RedisConfig(prefix="audit")  # Will find AUDIT_REDIS_CLIENT_HOST, etc.

"""

import base64
import os
import subprocess
from pathlib import Path
from typing import Any, Literal

import yaml

LayerName = Literal["layer0", "layer1", "layer2", "layer3"]


class SecretsProvider:
    """Provides unified access to secrets from vault or K8s."""

    def __init__(self, vault_dir: Path | None = None) -> None:
        """
        Initialize SecretsProvider.

        Args:
        ----
            vault_dir: Path to vault directory. If None, will try to find it in:
                1. KSTACK_VAULT_DIR environment variable
                2. ${KSTACK_ROOT}/vault from KSTACK_ROOT env var
                3. /home/lbrack/github/devops/kstack-lib/vault (development convention)

        """
        if vault_dir:
            self.vault_dir = vault_dir
        elif os.environ.get("KSTACK_VAULT_DIR"):
            self.vault_dir = Path(os.environ["KSTACK_VAULT_DIR"])
        elif os.environ.get("KSTACK_ROOT"):
            self.vault_dir = Path(os.environ["KSTACK_ROOT"]) / "vault"
        else:
            # Development convention: vault is in kstack-lib repo
            self.vault_dir = Path("/home/lbrack/github/devops/kstack-lib/vault")

    def get_current_environment(self) -> str:
        """
        Get the current environment (dev, staging, prod).

        Returns
        -------
            Environment name, defaults to 'dev'

        """
        return os.environ.get("KSTACK_ENV", "dev")

    def get_current_namespace(self) -> str | None:
        """
        Get the current Kubernetes namespace if running in K8s.

        Returns
        -------
            Current namespace name, or None if not in K8s

        """
        namespace_file = Path("/var/run/secrets/kubernetes.io/serviceaccount/namespace")
        if namespace_file.exists():
            return namespace_file.read_text().strip()
        return None

    def is_running_in_k8s(self) -> bool:
        """
        Check if running inside a Kubernetes pod.

        Returns
        -------
            True if running in K8s, False otherwise

        """
        return self.get_current_namespace() is not None

    def _convert_key_to_env_var(self, key: str) -> str:
        """
        Convert vault key to environment variable name.

        Examples:
        --------
            'redis-client-host' -> 'REDIS_CLIENT_HOST'
            'audit-redis-client-host' -> 'AUDIT_REDIS_CLIENT_HOST'

        Args:
        ----
            key: Vault key with hyphens

        Returns:
        -------
            Environment variable name with underscores and uppercase

        """
        return key.replace("-", "_").upper()

    def _load_vault_file(self, vault_file: Path) -> dict[str, Any]:
        """
        Load and parse a vault YAML file.

        Args:
        ----
            vault_file: Path to vault YAML file

        Returns:
        -------
            Parsed vault data as dictionary

        """
        if not vault_file.exists():
            return {}

        with open(vault_file) as f:
            data = yaml.safe_load(f)
            return data if data else {}

    def _can_access_secret(self, source_layer: str, target_layer: str, vault_data: dict[str, Any]) -> bool:
        """
        Check if a layer can access secrets from another layer.

        Args:
        ----
            source_layer: Layer requesting access (e.g., 'layer0')
            target_layer: Layer containing the secret (e.g., 'layer3')
            vault_data: Vault file data containing potential 'shared_with' key

        Returns:
        -------
            True if access is allowed, False otherwise

        Rules:
            - Same layer: always allowed
            - Different layer: allowed only if source_layer in vault_data['shared_with']

        """
        # Same layer always has access
        if source_layer == target_layer:
            return True

        # Check if target layer has explicitly shared with source layer
        shared_with = vault_data.get("shared_with", [])
        return source_layer in shared_with

    def load_secrets_from_vault(self, layer: LayerName) -> dict[str, str]:
        """
        Load secrets from vault YAML files for a specific layer.

        Loads secrets from the layer's own vault file and any other layers
        that have shared secrets with this layer.

        Args:
        ----
            layer: Layer name (layer0, layer1, layer2, layer3)

        Returns:
        -------
            Dictionary of secrets (key -> value)

        """
        env = self.get_current_environment()
        env_vault_dir = self.vault_dir / env

        if not env_vault_dir.exists():
            return {}

        secrets: dict[str, str] = {}

        # Load secrets from all layers (layer0, layer1, layer2, layer3)
        for layer_dir in ["layer0", "layer1", "layer2", "layer3"]:
            layer_path = env_vault_dir / layer_dir

            if not layer_path.exists():
                continue

            # Load all YAML files in this layer directory
            for vault_file in layer_path.glob("*.yaml"):
                vault_data = self._load_vault_file(vault_file)

                # Check if we can access these secrets
                if not self._can_access_secret(source_layer=layer, target_layer=layer_dir, vault_data=vault_data):
                    continue

                # Extract all key-value pairs (excluding metadata keys)
                for key, value in vault_data.items():
                    # Skip metadata keys
                    if key in ["shared_with", "description", "created", "status", "migration"]:
                        continue

                    # Convert value to string
                    secrets[key] = str(value)

        return secrets

    def load_secrets_from_k8s(self, layer: LayerName) -> dict[str, str]:
        """
        Load secrets from Kubernetes secrets.

        In K8s mode, secrets are already available as environment variables
        or can be read from K8s Secret resources.

        Args:
        ----
            layer: Layer name (layer0, layer1, layer2, layer3)

        Returns:
        -------
            Dictionary of secrets (key -> value)

        """
        namespace = self.get_current_namespace()
        if not namespace:
            return {}

        secrets: dict[str, str] = {}

        # Try to get secrets from K8s Secret named after the layer
        secret_name = f"{layer}-secrets"

        try:
            # Get all keys from the secret
            result = subprocess.run(
                [
                    "kubectl",
                    "get",
                    "secret",
                    secret_name,
                    "-n",
                    namespace,
                    "-o",
                    "json",
                ],
                capture_output=True,
                text=True,
                check=True,
            )

            import json

            secret_data = json.loads(result.stdout)
            encoded_data = secret_data.get("data", {})

            # Decode all base64-encoded values
            for key, encoded_value in encoded_data.items():
                decoded_value = base64.b64decode(encoded_value).decode("utf-8")
                secrets[key] = decoded_value

        except (subprocess.CalledProcessError, FileNotFoundError, json.JSONDecodeError):
            # K8s secret not found or kubectl not available
            pass

        return secrets

    def load_secrets(self, layer: LayerName) -> dict[str, str]:
        """
        Load secrets for a layer from appropriate source.

        Automatically detects whether to use vault (runmode) or K8s secrets (deployed).

        Args:
        ----
            layer: Layer name (layer0, layer1, layer2, layer3)

        Returns:
        -------
            Dictionary of secrets (key -> value)

        """
        if self.is_running_in_k8s():
            return self.load_secrets_from_k8s(layer)
        else:
            return self.load_secrets_from_vault(layer)

    def export_as_env_vars(self, secrets: dict[str, str], override_existing: bool = False) -> None:
        """
        Export secrets as environment variables.

        Args:
        ----
            secrets: Dictionary of secrets (vault keys -> values)
            override_existing: If True, override existing env vars. If False, respect existing values.

        """
        for key, value in secrets.items():
            env_var_name = self._convert_key_to_env_var(key)

            # Precedence: existing env var > vault secrets
            if not override_existing and env_var_name in os.environ:
                continue

            os.environ[env_var_name] = value


def load_secrets_for_layer(layer: LayerName, auto_export: bool = True) -> dict[str, str]:
    """
    Load secrets for a layer and optionally export as environment variables.

    This is the main entry point for applications to load their secrets.

    Args:
    ----
        layer: Layer name (layer0, layer1, layer2, layer3)
        auto_export: If True, automatically export secrets as environment variables

    Returns:
    -------
        Dictionary of secrets (vault keys -> values)

    Example:
    -------
        # Load secrets for Layer 0 application
        secrets = load_secrets_for_layer("layer0", auto_export=True)

        # Now AUDIT_REDIS_CLIENT_HOST, REDIS_CLIENT_HOST, etc. are available in os.environ
        from partsnap_rediscache.config import RedisConfig
        config = RedisConfig(prefix="audit")

    """
    provider = SecretsProvider()
    secrets = provider.load_secrets(layer)

    if auto_export:
        provider.export_as_env_vars(secrets, override_existing=False)

    return secrets
