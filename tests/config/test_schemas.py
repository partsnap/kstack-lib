"""Tests for configuration schemas."""

import pytest
from pydantic import ValidationError

from kstack_lib.config.schemas import (
    CloudCredentials,
    EnvironmentConfig,
    ProviderConfig,
    ProviderCredentials,
    ProviderFamily,
    ProviderImplementation,
    ServiceConfig,
)


class TestServiceConfig:
    """Tests for ServiceConfig model."""

    def test_service_config_minimal(self):
        """Test ServiceConfig with minimal fields."""
        config = ServiceConfig()
        assert config.endpoint_url is None
        assert config.presigned_url_domain is None

    def test_service_config_with_endpoint(self):
        """Test ServiceConfig with endpoint URL."""
        config = ServiceConfig(endpoint_url="http://localstack:4566")
        assert config.endpoint_url == "http://localstack:4566"
        assert config.presigned_url_domain is None

    def test_service_config_with_template_variables(self):
        """Test ServiceConfig with template variables."""
        config = ServiceConfig(
            endpoint_url="http://localstack.{{layer.namespace}}.svc.cluster.local:4566",
            presigned_url_domain="localstack.dev.partsnap.local",
        )
        assert "{{layer.namespace}}" in config.endpoint_url
        assert config.presigned_url_domain == "localstack.dev.partsnap.local"

    def test_service_config_allows_extra_fields(self):
        """Test that ServiceConfig allows additional fields."""
        config = ServiceConfig(endpoint_url="http://test:4566", custom_field="value")
        assert config.endpoint_url == "http://test:4566"
        # Pydantic stores extra fields but doesn't expose them as attributes


class TestProviderConfig:
    """Tests for ProviderConfig model."""

    def test_localstack_provider(self):
        """Test LocalStack provider configuration."""
        config = ProviderConfig(
            name="localstack",
            provider_family=ProviderFamily.AWS,
            provider_implementation=ProviderImplementation.LOCALSTACK,
            services={
                "s3": ServiceConfig(
                    endpoint_url="http://localstack.layer-3-global-infra.svc.cluster.local:4566",
                    presigned_url_domain="localstack.dev.partsnap.local",
                )
            },
            region="us-west-2",
            verify_ssl=False,
        )

        assert config.name == "localstack"
        assert config.provider_family == ProviderFamily.AWS
        assert config.provider_implementation == ProviderImplementation.LOCALSTACK
        assert "s3" in config.services
        assert config.region == "us-west-2"
        assert config.verify_ssl is False

    def test_aws_provider(self):
        """Test AWS provider configuration."""
        config = ProviderConfig(
            name="aws-dev",
            provider_family=ProviderFamily.AWS,
            provider_implementation=ProviderImplementation.AWS,
            services={"s3": ServiceConfig(presigned_url_domain=None)},
            region="us-west-2",
            verify_ssl=True,
        )

        assert config.name == "aws-dev"
        assert config.provider_implementation == ProviderImplementation.AWS
        assert config.verify_ssl is True

    def test_invalid_family_implementation_combo(self):
        """Test that invalid family/implementation combination fails."""
        with pytest.raises(ValidationError) as exc_info:
            ProviderConfig(
                name="invalid",
                provider_family=ProviderFamily.AWS,
                provider_implementation=ProviderImplementation.GCP,  # GCP impl with AWS family!
                region="us-west-2",
            )

        assert "not valid for family" in str(exc_info.value)

    def test_gcp_provider(self):
        """Test GCP provider configuration."""
        config = ProviderConfig(
            name="gcp-prod",
            provider_family=ProviderFamily.GCP,
            provider_implementation=ProviderImplementation.GCP,
            services={},
            region="us-central1",
        )

        assert config.provider_family == ProviderFamily.GCP
        assert config.provider_implementation == ProviderImplementation.GCP

    def test_provider_with_metadata(self):
        """Test provider configuration with metadata fields."""
        config = ProviderConfig(
            name="localstack",
            provider_family=ProviderFamily.AWS,
            provider_implementation=ProviderImplementation.LOCALSTACK,
            region="us-west-2",
            description="LocalStack for local development",
            created="2025-01-10",
            notes="Use with dev environment",
        )

        assert config.description == "LocalStack for local development"
        assert config.created == "2025-01-10"
        assert config.notes == "Use with dev environment"


class TestEnvironmentConfig:
    """Tests for EnvironmentConfig model."""

    def test_dev_environment(self):
        """Test development environment configuration."""
        config = EnvironmentConfig(
            environment="dev",
            deployment_targets={
                "layer3": {"provider": "localstack"},
                "layer1": {"provider": "localstack"},
            },
            allow_provider_override=True,
            description="Local development environment",
        )

        assert config.environment == "dev"
        assert config.deployment_targets["layer3"].provider == "localstack"
        assert config.deployment_targets["layer1"].provider == "localstack"
        assert config.allow_provider_override is True

    def test_testing_environment(self):
        """Test testing environment configuration."""
        config = EnvironmentConfig(
            environment="testing",
            deployment_targets={
                "layer3": {"provider": "localstack"},
                "layer1": {"provider": "localstack"},
            },
            allow_provider_override=False,
        )

        assert config.environment == "testing"
        assert config.allow_provider_override is False

    def test_invalid_layer_key(self):
        """Test that invalid layer keys are rejected."""
        with pytest.raises(ValidationError) as exc_info:
            EnvironmentConfig(
                environment="dev",
                deployment_targets={
                    "layer3": {"provider": "localstack"},
                    "layer2": {"provider": "localstack"},  # Layer 2 doesn't use cloud services!
                },
            )

        assert "Invalid layer keys" in str(exc_info.value)
        assert "layer2" in str(exc_info.value)

    def test_layer0_not_allowed(self):
        """Test that Layer 0 is not allowed in deployment targets."""
        with pytest.raises(ValidationError) as exc_info:
            EnvironmentConfig(
                environment="dev",
                deployment_targets={
                    "layer3": {"provider": "localstack"},
                    "layer0": {"provider": "localstack"},  # Layer 0 is applications!
                },
            )

        assert "Invalid layer keys" in str(exc_info.value)
        assert "layer0" in str(exc_info.value)


class TestProviderCredentials:
    """Tests for ProviderCredentials model."""

    def test_localstack_credentials(self):
        """Test LocalStack credentials."""
        creds = ProviderCredentials(
            aws_access_key_id="test",
            aws_secret_access_key="test",
        )

        assert creds.aws_access_key_id == "test"
        assert creds.aws_secret_access_key == "test"
        assert creds.aws_session_token is None

    def test_aws_credentials_with_session_token(self):
        """Test AWS credentials with temporary session token."""
        creds = ProviderCredentials(
            aws_access_key_id="AKIA...",
            aws_secret_access_key="secret",
            aws_session_token="session_token",
        )

        assert creds.aws_access_key_id == "AKIA..."
        assert creds.aws_session_token == "session_token"

    def test_gcp_credentials(self):
        """Test GCP credentials."""
        creds = ProviderCredentials(
            gcp_credentials_json='{"type": "service_account"}',
            gcp_project_id="my-project",
        )

        assert creds.gcp_credentials_json == '{"type": "service_account"}'
        assert creds.gcp_project_id == "my-project"

    def test_azure_credentials(self):
        """Test Azure credentials."""
        creds = ProviderCredentials(
            azure_subscription_id="sub-123",
            azure_tenant_id="tenant-456",
            azure_client_id="client-789",
            azure_client_secret="secret",
        )

        assert creds.azure_subscription_id == "sub-123"
        assert creds.azure_client_secret == "secret"

    def test_empty_credentials_fails(self):
        """Test that credentials with no fields fails validation."""
        with pytest.raises(ValidationError) as exc_info:
            ProviderCredentials()

        assert "At least one set of credentials must be provided" in str(exc_info.value)


class TestCloudCredentials:
    """Tests for CloudCredentials model."""

    def test_cloud_credentials_dev(self):
        """Test cloud credentials for dev environment."""
        creds = CloudCredentials(
            providers={
                "localstack": ProviderCredentials(
                    aws_access_key_id="test",
                    aws_secret_access_key="test",
                ),
                "aws-dev": ProviderCredentials(
                    aws_access_key_id="AKIA_DEV",
                    aws_secret_access_key="dev_secret",
                ),
            },
            description="Development environment credentials",
            created="2025-01-10",
        )

        assert "localstack" in creds.providers
        assert "aws-dev" in creds.providers
        assert creds.providers["localstack"].aws_access_key_id == "test"
        assert creds.providers["aws-dev"].aws_access_key_id == "AKIA_DEV"

    def test_cloud_credentials_multiple_providers(self):
        """Test cloud credentials with multiple provider types."""
        creds = CloudCredentials(
            providers={
                "localstack": ProviderCredentials(
                    aws_access_key_id="test",
                    aws_secret_access_key="test",
                ),
                "aws-staging": ProviderCredentials(
                    aws_access_key_id="AKIA_STAGING",
                    aws_secret_access_key="staging_secret",
                ),
                "gcp-prod": ProviderCredentials(
                    gcp_credentials_json='{"type": "service_account"}',
                    gcp_project_id="prod-project",
                ),
            }
        )

        assert len(creds.providers) == 3
        assert "localstack" in creds.providers
        assert "aws-staging" in creds.providers
        assert "gcp-prod" in creds.providers


class TestProviderFamilyImplementationValidation:
    """Tests for provider family and implementation validation."""

    def test_all_aws_family_implementations(self):
        """Test that all AWS family implementations are valid."""
        for impl in [
            ProviderImplementation.LOCALSTACK,
            ProviderImplementation.AWS,
            ProviderImplementation.DIGITALOCEAN,
            ProviderImplementation.MINIO,
        ]:
            config = ProviderConfig(
                name=f"test-{impl.value}",
                provider_family=ProviderFamily.AWS,
                provider_implementation=impl,
                region="us-west-2",
            )
            assert config.provider_family == ProviderFamily.AWS
            assert config.provider_implementation == impl

    def test_gcp_family_only_gcp_implementation(self):
        """Test that GCP family only accepts GCP implementation."""
        config = ProviderConfig(
            name="test-gcp",
            provider_family=ProviderFamily.GCP,
            provider_implementation=ProviderImplementation.GCP,
            region="us-central1",
        )
        assert config.provider_implementation == ProviderImplementation.GCP

        # Test that AWS implementation fails with GCP family
        with pytest.raises(ValidationError):
            ProviderConfig(
                name="invalid",
                provider_family=ProviderFamily.GCP,
                provider_implementation=ProviderImplementation.AWS,
                region="us-central1",
            )

    def test_azure_family_only_azure_implementation(self):
        """Test that Azure family only accepts Azure implementation."""
        config = ProviderConfig(
            name="test-azure",
            provider_family=ProviderFamily.AZURE,
            provider_implementation=ProviderImplementation.AZURE,
            region="eastus",
        )
        assert config.provider_implementation == ProviderImplementation.AZURE

        # Test that LocalStack implementation fails with Azure family
        with pytest.raises(ValidationError):
            ProviderConfig(
                name="invalid",
                provider_family=ProviderFamily.AZURE,
                provider_implementation=ProviderImplementation.LOCALSTACK,
                region="eastus",
            )
