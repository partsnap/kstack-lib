"""Tests for configuration loading functions."""

import pytest
import yaml

from kstack_lib.config import ConfigMap, KStackEnvironment, KStackLayer
from kstack_lib.config.loaders import (
    ConfigurationError,
    _resolve_dict_templates,
    _resolve_template_variables,
    get_cloud_provider,
    load_cloud_credentials,
    load_environment_config,
    load_provider_config,
)
from kstack_lib.config.schemas import ProviderFamily, ProviderImplementation


class TestTemplateResolution:
    """Tests for template variable resolution."""

    def test_resolve_simple_variable(self):
        """Test resolving a simple variable."""
        context = {"layer": {"namespace": "layer-3-global-infra"}}
        result = _resolve_template_variables("http://{{layer.namespace}}:4566", context)
        assert result == "http://layer-3-global-infra:4566"

    def test_resolve_multiple_variables(self):
        """Test resolving multiple variables in one string."""
        context = {"layer": {"namespace": "layer-3-global-infra", "number": 3}}
        result = _resolve_template_variables("Layer {{layer.number}} at {{layer.namespace}}", context)
        assert result == "Layer 3 at layer-3-global-infra"

    def test_resolve_missing_variable_fails(self):
        """Test that missing variable raises error."""
        context = {"layer": {"namespace": "layer-3-global-infra"}}
        with pytest.raises(ConfigurationError) as exc_info:
            _resolve_template_variables("{{missing.var}}", context)
        assert "not found in context" in str(exc_info.value)

    def test_resolve_dict_templates(self):
        """Test resolving templates in nested dict."""
        data = {
            "endpoint": "http://{{layer.namespace}}:{{port}}",
            "nested": {
                "value": "Layer {{layer.number}}",
            },
        }
        context = {"layer": {"namespace": "layer-3-global-infra", "number": 3}, "port": "4566"}
        result = _resolve_dict_templates(data, context)

        assert result["endpoint"] == "http://layer-3-global-infra:4566"
        assert result["nested"]["value"] == "Layer 3"

    def test_no_templates_unchanged(self):
        """Test that strings without templates are unchanged."""
        context = {"layer": {"namespace": "test"}}
        result = _resolve_template_variables("no templates here", context)
        assert result == "no templates here"


class TestLoadEnvironmentConfig:
    """Tests for load_environment_config()."""

    def test_load_dev_environment(self, tmp_path):
        """Test loading dev environment configuration."""
        config_dir = tmp_path / "environments"
        config_dir.mkdir()

        # Create dev.yaml
        dev_config = {
            "environment": "dev",
            "deployment_targets": {
                "layer3": {"provider": "localstack"},
                "layer1": {"provider": "localstack"},
            },
            "allow_provider_override": True,
            "description": "Development environment",
        }

        with open(config_dir / "dev.yaml", "w") as f:
            yaml.dump(dev_config, f)

        # Load and verify
        config = load_environment_config(KStackEnvironment.DEVELOPMENT, config_dir=config_dir)

        assert config.environment == "dev"
        assert config.deployment_targets["layer3"].provider == "localstack"
        assert config.deployment_targets["layer1"].provider == "localstack"
        assert config.allow_provider_override is True

    def test_load_missing_environment_fails(self, tmp_path):
        """Test that loading missing environment fails."""
        config_dir = tmp_path / "environments"
        config_dir.mkdir()

        with pytest.raises(ConfigurationError) as exc_info:
            load_environment_config(KStackEnvironment.STAGING, config_dir=config_dir)

        assert "not found" in str(exc_info.value)

    def test_load_invalid_yaml_fails(self, tmp_path):
        """Test that invalid YAML fails."""
        config_dir = tmp_path / "environments"
        config_dir.mkdir()

        with open(config_dir / "dev.yaml", "w") as f:
            f.write("invalid: yaml: syntax:")

        with pytest.raises(ConfigurationError) as exc_info:
            load_environment_config(KStackEnvironment.DEVELOPMENT, config_dir=config_dir)

        assert "Failed to parse" in str(exc_info.value)


class TestLoadProviderConfig:
    """Tests for load_provider_config()."""

    def test_load_localstack_provider_with_templates(self, tmp_path):
        """Test loading LocalStack provider with template resolution."""
        config_dir = tmp_path / "providers"
        config_dir.mkdir()

        # Create localstack.yaml with templates
        localstack_config = {
            "name": "localstack",
            "provider_family": "aws",
            "provider_implementation": "localstack",
            "services": {
                "s3": {
                    "endpoint_url": "http://localstack.{{layer.namespace}}.svc.cluster.local:4566",
                    "presigned_url_domain": "localstack.dev.partsnap.local",
                }
            },
            "region": "us-west-2",
            "verify_ssl": False,
        }

        with open(config_dir / "localstack.yaml", "w") as f:
            yaml.dump(localstack_config, f)

        # Load and verify template resolution
        config = load_provider_config(
            "localstack",
            layer=KStackLayer.LAYER_3_GLOBAL_INFRA,
            environment=KStackEnvironment.DEVELOPMENT,
            config_dir=config_dir,
        )

        assert config.name == "localstack"
        assert config.provider_family == ProviderFamily.AWS
        assert config.provider_implementation == ProviderImplementation.LOCALSTACK
        # Template should be resolved!
        assert config.services["s3"].endpoint_url == "http://localstack.layer-3-global-infra.svc.cluster.local:4566"
        assert config.services["s3"].presigned_url_domain == "localstack.dev.partsnap.local"

    def test_template_resolution_different_layers(self, tmp_path):
        """Test that templates resolve differently for different layers."""
        config_dir = tmp_path / "providers"
        config_dir.mkdir()

        localstack_config = {
            "name": "localstack",
            "provider_family": "aws",
            "provider_implementation": "localstack",
            "services": {"s3": {"endpoint_url": "http://localstack.{{layer.namespace}}.svc.cluster.local:4566"}},
            "region": "us-west-2",
        }

        with open(config_dir / "localstack.yaml", "w") as f:
            yaml.dump(localstack_config, f)

        # Load for Layer 3
        config_layer3 = load_provider_config(
            "localstack",
            layer=KStackLayer.LAYER_3_GLOBAL_INFRA,
            environment=KStackEnvironment.DEVELOPMENT,
            config_dir=config_dir,
        )
        assert "layer-3-global-infra" in config_layer3.services["s3"].endpoint_url

        # Load for Layer 1
        config_layer1 = load_provider_config(
            "localstack",
            layer=KStackLayer.LAYER_1_TENANT_INFRA,
            environment=KStackEnvironment.DEVELOPMENT,
            config_dir=config_dir,
        )
        assert "layer-1-tenant-infra" in config_layer1.services["s3"].endpoint_url

    def test_load_aws_provider_no_templates(self, tmp_path):
        """Test loading AWS provider (no templates)."""
        config_dir = tmp_path / "providers"
        config_dir.mkdir()

        aws_config = {
            "name": "aws-dev",
            "provider_family": "aws",
            "provider_implementation": "aws",
            "services": {"s3": {"presigned_url_domain": None}},
            "region": "us-west-2",
            "verify_ssl": True,
        }

        with open(config_dir / "aws-dev.yaml", "w") as f:
            yaml.dump(aws_config, f)

        config = load_provider_config(
            "aws-dev",
            layer=KStackLayer.LAYER_3_GLOBAL_INFRA,
            environment=KStackEnvironment.DEVELOPMENT,
            config_dir=config_dir,
        )

        assert config.name == "aws-dev"
        assert config.verify_ssl is True


class TestLoadCloudCredentials:
    """Tests for load_cloud_credentials()."""

    def test_load_credentials_dev(self, tmp_path):
        """Test loading dev credentials."""
        vault_dir = tmp_path / "vault"
        creds_dir = vault_dir / "dev" / "layer3"
        creds_dir.mkdir(parents=True)

        # Create cloud-credentials.yaml
        creds = {
            "providers": {
                "localstack": {
                    "aws_access_key_id": "test",
                    "aws_secret_access_key": "test",
                },
                "aws-dev": {
                    "aws_access_key_id": "AKIA_DEV",
                    "aws_secret_access_key": "dev_secret",
                },
            },
            "created": "2025-01-10",
        }

        with open(creds_dir / "cloud-credentials.yaml", "w") as f:
            yaml.dump(creds, f)

        # Load and verify
        loaded = load_cloud_credentials(
            environment=KStackEnvironment.DEVELOPMENT,
            layer=KStackLayer.LAYER_3_GLOBAL_INFRA,
            vault_dir=vault_dir,
        )

        assert "localstack" in loaded.providers
        assert "aws-dev" in loaded.providers
        assert loaded.providers["localstack"].aws_access_key_id == "test"
        assert loaded.providers["aws-dev"].aws_access_key_id == "AKIA_DEV"

    def test_load_missing_credentials_fails(self, tmp_path):
        """Test that missing credentials file fails."""
        vault_dir = tmp_path / "vault"
        vault_dir.mkdir()

        with pytest.raises(ConfigurationError) as exc_info:
            load_cloud_credentials(
                environment=KStackEnvironment.DEVELOPMENT,
                layer=KStackLayer.LAYER_3_GLOBAL_INFRA,
                vault_dir=vault_dir,
            )

        assert "not found" in str(exc_info.value).lower()


class TestGetCloudProvider:
    """Tests for get_cloud_provider() - full integration."""

    def test_get_cloud_provider_localstack(self, tmp_path):
        """Test getting complete LocalStack provider config."""
        # Setup directory structure
        config_root = tmp_path / "config"
        vault_root = tmp_path / "vault"
        (config_root / "environments").mkdir(parents=True)
        (config_root / "providers").mkdir(parents=True)
        (vault_root / "dev" / "layer3").mkdir(parents=True)

        # Create environment config
        env_config = {
            "environment": "dev",
            "deployment_targets": {
                "layer3": {"provider": "localstack"},
                "layer1": {"provider": "localstack"},
            },
            "allow_provider_override": True,
        }
        with open(config_root / "environments" / "dev.yaml", "w") as f:
            yaml.dump(env_config, f)

        # Create provider config
        provider_config = {
            "name": "localstack",
            "provider_family": "aws",
            "provider_implementation": "localstack",
            "services": {
                "s3": {
                    "endpoint_url": "http://localstack.{{layer.namespace}}.svc.cluster.local:4566",
                }
            },
            "region": "us-west-2",
            "verify_ssl": False,
        }
        with open(config_root / "providers" / "localstack.yaml", "w") as f:
            yaml.dump(provider_config, f)

        # Create credentials
        credentials = {
            "providers": {
                "localstack": {
                    "aws_access_key_id": "test",
                    "aws_secret_access_key": "test",
                }
            }
        }
        with open(vault_root / "dev" / "layer3" / "cloud-credentials.yaml", "w") as f:
            yaml.dump(credentials, f)

        # Get cloud provider
        cfg = ConfigMap(layer=KStackLayer.LAYER_3_GLOBAL_INFRA, environment=KStackEnvironment.DEVELOPMENT)
        provider, creds = get_cloud_provider(
            cfg,
            service="s3",
            config_root=config_root,
            vault_root=vault_root,
        )

        # Verify provider config
        assert provider.name == "localstack"
        assert provider.provider_family == ProviderFamily.AWS
        assert "layer-3-global-infra" in provider.services["s3"].endpoint_url

        # Verify credentials
        assert creds["aws_access_key_id"] == "test"
        assert creds["aws_secret_access_key"] == "test"

    def test_get_cloud_provider_with_override(self, tmp_path):
        """Test provider override functionality."""
        # Setup
        config_root = tmp_path / "config"
        vault_root = tmp_path / "vault"
        (config_root / "environments").mkdir(parents=True)
        (config_root / "providers").mkdir(parents=True)
        (vault_root / "dev" / "layer3").mkdir(parents=True)

        # Environment allows override
        env_config = {
            "environment": "dev",
            "deployment_targets": {"layer3": {"provider": "localstack"}},
            "allow_provider_override": True,
        }
        with open(config_root / "environments" / "dev.yaml", "w") as f:
            yaml.dump(env_config, f)

        # Create aws-dev provider
        aws_config = {
            "name": "aws-dev",
            "provider_family": "aws",
            "provider_implementation": "aws",
            "services": {},
            "region": "us-west-2",
            "verify_ssl": True,
        }
        with open(config_root / "providers" / "aws-dev.yaml", "w") as f:
            yaml.dump(aws_config, f)

        # Credentials for aws-dev
        credentials = {
            "providers": {
                "aws-dev": {
                    "aws_access_key_id": "AKIA_DEV",
                    "aws_secret_access_key": "dev_secret",
                }
            }
        }
        with open(vault_root / "dev" / "layer3" / "cloud-credentials.yaml", "w") as f:
            yaml.dump(credentials, f)

        # Get with override
        cfg = ConfigMap(layer=KStackLayer.LAYER_3_GLOBAL_INFRA, environment=KStackEnvironment.DEVELOPMENT)
        provider, creds = get_cloud_provider(
            cfg,
            service="s3",
            override_provider="aws-dev",
            config_root=config_root,
            vault_root=vault_root,
        )

        # Should get aws-dev, not localstack!
        assert provider.name == "aws-dev"
        assert provider.provider_implementation == ProviderImplementation.AWS
        assert creds["aws_access_key_id"] == "AKIA_DEV"

    def test_get_cloud_provider_override_not_allowed(self, tmp_path):
        """Test that override fails when not allowed."""
        config_root = tmp_path / "config"
        vault_root = tmp_path / "vault"
        (config_root / "environments").mkdir(parents=True)

        # Environment disallows override
        env_config = {
            "environment": "test",
            "deployment_targets": {"layer3": {"provider": "localstack"}},
            "allow_provider_override": False,  # Not allowed!
        }
        with open(config_root / "environments" / "test.yaml", "w") as f:
            yaml.dump(env_config, f)

        cfg = ConfigMap(layer=KStackLayer.LAYER_3_GLOBAL_INFRA, environment=KStackEnvironment.TESTING)

        with pytest.raises(ConfigurationError) as exc_info:
            get_cloud_provider(
                cfg,
                service="s3",
                override_provider="aws-dev",
                config_root=config_root,
                vault_root=vault_root,
            )

        assert "not allowed" in str(exc_info.value)
