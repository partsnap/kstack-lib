"""
Configuration loading functions for cloud provider abstraction.

This module provides functions to load and parse configuration files:
- Environment configuration (config/environments/*.yaml)
- Provider configuration (config/providers/*.yaml)
- Cloud credentials (vault/**/cloud-credentials.yaml)

Features:
- Template variable resolution (e.g., {{layer.namespace}})
- Validation via Pydantic models
- Integration with ConfigMap for layer/environment context
"""

import re
from pathlib import Path
from typing import Any

import yaml

from kstack_lib.config.configmap import ConfigMap
from kstack_lib.config.schemas import (
    CloudCredentials,
    EnvironmentConfig,
    ProviderConfig,
)
from kstack_lib.types import KStackEnvironment, KStackLayer


class ConfigurationError(Exception):
    """Raised when configuration loading or validation fails."""

    pass


def _resolve_template_variables(value: str, context: dict[str, Any]) -> str:
    """
    Resolve template variables in a string.

    Template syntax: {{variable.path}}

    Examples:
    --------
        {{layer.namespace}} → layer-3-global-infra
        {{layer.number}} → 3
        {{environment}} → dev

    Args:
    ----
        value: String potentially containing template variables
        context: Dictionary of available variables

    Returns:
    -------
        String with variables resolved

    Raises:
    ------
        ConfigurationError: If a variable is referenced but not in context

    """
    # Find all template variables: {{var.path}}
    pattern = r"\{\{([^}]+)\}\}"
    matches = re.findall(pattern, value)

    if not matches:
        return value

    result = value
    for var_path in matches:
        # Split path: "layer.namespace" → ["layer", "namespace"]
        parts = var_path.strip().split(".")

        # Navigate context dict
        current = context
        try:
            for part in parts:
                current = current[part]
        except (KeyError, TypeError):
            raise ConfigurationError(
                f"Template variable '{var_path}' not found in context. " f"Available: {list(context.keys())}"
            )

        # Replace {{var.path}} with resolved value
        result = result.replace(f"{{{{{var_path}}}}}", str(current))

    return result


def _resolve_dict_templates(data: dict[str, Any], context: dict[str, Any]) -> dict[str, Any]:
    """
    Recursively resolve template variables in a dictionary.

    Args:
    ----
        data: Dictionary potentially containing template variables
        context: Dictionary of available variables

    Returns:
    -------
        Dictionary with all template variables resolved

    """
    result = {}
    for key, value in data.items():
        if isinstance(value, str):
            result[key] = _resolve_template_variables(value, context)
        elif isinstance(value, dict):
            result[key] = _resolve_dict_templates(value, context)
        elif isinstance(value, list):
            result[key] = [_resolve_dict_templates(item, context) if isinstance(item, dict) else item for item in value]
        else:
            result[key] = value
    return result


def load_environment_config(environment: KStackEnvironment, config_dir: Path | None = None) -> EnvironmentConfig:
    """
    Load environment configuration from YAML file.

    Args:
    ----
        environment: Environment to load (dev, testing, staging, production)
        config_dir: Config directory path (defaults to <repo>/config/environments)

    Returns:
    -------
        Validated EnvironmentConfig

    Raises:
    ------
        ConfigurationError: If file not found or validation fails

    """
    if config_dir is None:
        # Default: config/environments/ relative to kstack-lib root
        # For now, assume caller passes correct path
        raise ConfigurationError("config_dir must be provided")

    config_file = config_dir / f"{environment.value}.yaml"

    if not config_file.exists():
        raise ConfigurationError(
            f"Environment configuration not found: {config_file}\n"
            f"Available files: {list(config_dir.glob('*.yaml'))}"
        )

    try:
        with open(config_file) as f:
            data = yaml.safe_load(f)
    except Exception as e:
        raise ConfigurationError(f"Failed to parse {config_file}: {e}")

    try:
        return EnvironmentConfig(**data)
    except Exception as e:
        raise ConfigurationError(f"Invalid environment configuration in {config_file}: {e}")


def load_provider_config(
    provider_name: str, layer: KStackLayer, environment: KStackEnvironment, config_dir: Path | None = None
) -> ProviderConfig:
    """
    Load provider configuration from YAML file with template resolution.

    Template variables available:
    - {{layer.namespace}}: layer-3-global-infra, layer-1-tenant-infra, etc.
    - {{layer.number}}: 3, 1, etc.
    - {{layer.name}}: layer3, layer1, etc.
    - {{environment}}: dev, testing, staging, production

    Args:
    ----
        provider_name: Provider name (e.g., 'localstack', 'aws-dev')
        layer: Layer context for template variable resolution
        environment: Environment context for template variables
        config_dir: Config directory path (defaults to <repo>/config/providers)

    Returns:
    -------
        Validated ProviderConfig with templates resolved

    Raises:
    ------
        ConfigurationError: If file not found or validation fails

    """
    if config_dir is None:
        raise ConfigurationError("config_dir must be provided")

    config_file = config_dir / f"{provider_name}.yaml"

    if not config_file.exists():
        raise ConfigurationError(
            f"Provider configuration not found: {config_file}\n"
            f"Available providers: {list(config_dir.glob('*.yaml'))}"
        )

    try:
        with open(config_file) as f:
            raw_data = yaml.safe_load(f)
    except Exception as e:
        raise ConfigurationError(f"Failed to parse {config_file}: {e}")

    # Template variable context
    context = {
        "layer": {
            "namespace": layer.namespace,
            "number": layer.number,
            "name": f"layer{layer.number}",
        },
        "environment": environment.value,
    }

    # Resolve template variables
    try:
        resolved_data = _resolve_dict_templates(raw_data, context)
    except ConfigurationError as e:
        raise ConfigurationError(f"Template resolution failed in {config_file}: {e}")

    # Validate with Pydantic
    try:
        return ProviderConfig(**resolved_data)
    except Exception as e:
        raise ConfigurationError(f"Invalid provider configuration in {config_file}: {e}")


def load_cloud_credentials(
    environment: KStackEnvironment, layer: KStackLayer, vault_dir: Path | None = None
) -> CloudCredentials:
    """
    Load cloud credentials from Age-encrypted vault.

    Args:
    ----
        environment: Environment (dev, testing, staging, production)
        layer: Layer (used to find vault/{env}/layer{X}/cloud-credentials.yaml)
        vault_dir: Vault directory path (defaults to <repo>/vault)

    Returns:
    -------
        Validated CloudCredentials

    Raises:
    ------
        ConfigurationError: If file not found or validation fails

    Note:
    ----
        This function expects the vault to be DECRYPTED (cloud-credentials.yaml).
        Use `partsecrets reveal` to decrypt before loading.

    """
    if vault_dir is None:
        raise ConfigurationError("vault_dir must be provided")

    creds_file = vault_dir / environment.value / f"layer{layer.number}" / "cloud-credentials.yaml"
    vault_layer_dir = creds_file.parent

    if not creds_file.exists():
        # Check if vault is encrypted by looking for any secret.* file without its decrypted counterpart
        # In partsecrets, all files are encrypted/decrypted together, so if one is encrypted, all are
        is_vault_encrypted = False
        if vault_layer_dir.exists():
            for secret_file in vault_layer_dir.glob("secret.*"):
                # Get the decrypted filename by removing "secret." prefix
                decrypted_name = secret_file.name.replace("secret.", "", 1)
                decrypted_file = vault_layer_dir / decrypted_name
                if not decrypted_file.exists():
                    is_vault_encrypted = True
                    break

        if is_vault_encrypted:
            raise ConfigurationError(
                f"Cloud credentials not decrypted: {creds_file}\n"
                f"Vault contains encrypted files in: {vault_layer_dir}\n"
                f"\n"
                f"Please decrypt the vault:\n"
                f"  cd {vault_dir.parent}\n"
                f"  partsecrets reveal --team {environment.value}\n"
            )
        else:
            raise ConfigurationError(
                f"Cloud credentials not found: {creds_file}\n" f"Vault directory: {vault_layer_dir}\n"
            )

    try:
        with open(creds_file) as f:
            data = yaml.safe_load(f)
    except Exception as e:
        raise ConfigurationError(f"Failed to parse {creds_file}: {e}")

    try:
        return CloudCredentials(**data)
    except Exception as e:
        raise ConfigurationError(f"Invalid cloud credentials in {creds_file}: {e}")


def get_cloud_provider(
    cfg: ConfigMap,
    service: str,
    override_provider: str | None = None,
    config_root: Path | None = None,
    vault_root: Path | None = None,
) -> tuple[ProviderConfig, dict[str, Any]]:
    """
    Get cloud provider configuration and credentials.

    This is the main entry point for getting complete provider info.

    Args:
    ----
        cfg: ConfigMap with layer and environment
        service: Service name (s3, sqs, secretsmanager, etc.)
        override_provider: Optional provider override for debugging
        config_root: Root of config directory (defaults to auto-detect)
        vault_root: Root of vault directory (defaults to auto-detect)

    Returns:
    -------
        Tuple of (ProviderConfig, credentials_dict)

    Raises:
    ------
        ConfigurationError: If configuration or credentials cannot be loaded

    """
    if config_root is None:
        raise ConfigurationError("config_root must be provided")
    if vault_root is None:
        raise ConfigurationError("vault_root must be provided")

    # Load environment config
    env_config = load_environment_config(
        cfg.environment,
        config_dir=config_root / "environments",
    )

    # Determine provider name
    layer_key = f"layer{cfg.layer.number}"
    if layer_key not in env_config.deployment_targets:
        raise ConfigurationError(
            f"No deployment target configured for {layer_key} in {cfg.environment.value} environment"
        )

    provider_name = env_config.deployment_targets[layer_key].provider

    # Check override
    if override_provider:
        if not env_config.allow_provider_override:
            raise ConfigurationError(
                f"Provider override not allowed in {cfg.environment.value} environment. "
                f"Set allow_provider_override: true in config/environments/{cfg.environment.value}.yaml"
            )
        provider_name = override_provider

    # Load provider config
    provider_config = load_provider_config(
        provider_name,
        layer=cfg.layer,
        environment=cfg.environment,
        config_dir=config_root / "providers",
    )

    # Load credentials
    cloud_creds = load_cloud_credentials(
        environment=cfg.environment,
        layer=cfg.layer,
        vault_dir=vault_root,
    )

    # Get credentials for this provider
    if provider_name not in cloud_creds.providers:
        raise ConfigurationError(
            f"No credentials found for provider '{provider_name}' in vault. "
            f"Available: {list(cloud_creds.providers.keys())}"
        )

    provider_creds = cloud_creds.providers[provider_name]

    # Return provider config and credentials as dict
    return provider_config, provider_creds.model_dump(exclude_none=True)
