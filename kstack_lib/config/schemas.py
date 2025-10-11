"""
Configuration schemas for cloud provider abstraction.

This module defines Pydantic models for:
- Environment configuration (config/environments/*.yaml)
- Provider configuration (config/providers/*.yaml)
- Cloud credentials (vault/**/cloud-credentials.yaml)
"""

from enum import Enum
from typing import Annotated

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator


class ProviderFamily(str, Enum):
    """Cloud provider family - which SDK/client library to use."""

    AWS = "aws"  # boto3/aioboto3 (S3, SQS, Secrets Manager)
    GCP = "gcp"  # google-cloud-* libraries
    AZURE = "azure"  # azure-sdk-for-python


class ProviderImplementation(str, Enum):
    """Cloud provider implementation - how to configure the SDK."""

    # AWS family
    LOCALSTACK = "localstack"  # LocalStack (local AWS emulation)
    AWS = "aws"  # Real AWS
    DIGITALOCEAN = "digitalocean"  # DigitalOcean Spaces (S3-compatible)
    MINIO = "minio"  # MinIO (on-premises S3-compatible)

    # GCP family
    GCP = "gcp"  # Real GCP

    # Azure family
    AZURE = "azure"  # Real Azure


class ServiceConfig(BaseModel):
    """Configuration for a specific cloud service (S3, SQS, etc.)."""

    endpoint_url: str | None = Field(
        default=None,
        description="Service endpoint URL. None means use provider defaults (e.g., AWS endpoints). "
        "Can contain template variables like {{layer.namespace}}",
    )
    presigned_url_domain: str | None = Field(
        default=None,
        description="Domain to use for presigned URLs. None means use service-generated URLs. "
        "Example: 'localstack.dev.partsnap.local'",
    )

    model_config = ConfigDict(extra="allow")  # Allow additional service-specific config


class ProviderConfig(BaseModel):
    """
    Provider configuration (config/providers/*.yaml).

    Examples
    --------
        LocalStack:
            name: localstack
            provider_family: aws
            provider_implementation: localstack
            services:
              s3:
                endpoint_url: "http://localstack.{{layer.namespace}}.svc.cluster.local:4566"
                presigned_url_domain: "localstack.dev.partsnap.local"
            region: us-west-2
            verify_ssl: false

        AWS:
            name: aws-dev
            provider_family: aws
            provider_implementation: aws
            services:
              s3:
                presigned_url_domain: null
            region: us-west-2
            verify_ssl: true

    """

    name: Annotated[str, Field(description="Unique provider name (e.g., 'localstack', 'aws-dev')")]
    provider_family: Annotated[ProviderFamily, Field(description="Provider family (AWS, GCP, Azure)")]
    provider_implementation: Annotated[
        ProviderImplementation, Field(description="Specific implementation (localstack, aws, etc.)")
    ]

    services: Annotated[
        dict[str, ServiceConfig],
        Field(
            default_factory=dict,
            description="Service-specific configuration (s3, sqs, secretsmanager)",
        ),
    ]

    region: Annotated[str, Field(description="Cloud region (e.g., 'us-west-2')")]
    verify_ssl: Annotated[bool, Field(default=True, description="Verify SSL certificates")]

    # Optional metadata
    description: str | None = None
    created: str | None = None
    notes: str | None = None

    @model_validator(mode="after")
    def validate_family_implementation_match(self) -> "ProviderConfig":
        """Validate that implementation matches family."""
        family_implementations = {
            ProviderFamily.AWS: {
                ProviderImplementation.LOCALSTACK,
                ProviderImplementation.AWS,
                ProviderImplementation.DIGITALOCEAN,
                ProviderImplementation.MINIO,
            },
            ProviderFamily.GCP: {ProviderImplementation.GCP},
            ProviderFamily.AZURE: {ProviderImplementation.AZURE},
        }

        allowed = family_implementations.get(self.provider_family, set())
        if self.provider_implementation not in allowed:
            raise ValueError(
                f"Provider implementation '{self.provider_implementation}' "
                f"not valid for family '{self.provider_family}'. "
                f"Allowed: {', '.join(impl.value for impl in allowed)}"
            )

        return self


class LayerDeploymentTarget(BaseModel):
    """Deployment target for a specific layer."""

    provider: Annotated[str, Field(description="Provider name (references config/providers/*.yaml)")]


class EnvironmentConfig(BaseModel):
    """
    Environment configuration (config/environments/*.yaml).

    Example:
    -------
        environment: dev
        deployment_targets:
          layer3:
            provider: localstack
          layer1:
            provider: localstack
        allow_provider_override: true
        description: "Local development environment"

    """

    environment: Annotated[str, Field(description="Environment name (dev, testing, staging, production)")]

    deployment_targets: Annotated[
        dict[str, LayerDeploymentTarget],
        Field(
            description="Deployment target (provider) for each layer. "
            "Keys: layer3, layer1 (Layer 2 and 0 don't use cloud services)"
        ),
    ]

    allow_provider_override: Annotated[
        bool,
        Field(
            default=False,
            description="Allow runtime provider override for debugging (e.g., --override-provider aws-dev)",
        ),
    ]

    # Optional metadata
    description: str | None = None
    created: str | None = None

    @field_validator("deployment_targets")
    @classmethod
    def validate_layer_keys(cls, v: dict[str, LayerDeploymentTarget]) -> dict[str, LayerDeploymentTarget]:
        """Validate that only layer3 and layer1 are specified."""
        allowed_layers = {"layer3", "layer1"}
        invalid_layers = set(v.keys()) - allowed_layers

        if invalid_layers:
            raise ValueError(
                f"Invalid layer keys: {invalid_layers}. "
                f"Only layer3 and layer1 are supported (Layer 2 and 0 don't use cloud services)"
            )

        return v


class ProviderCredentials(BaseModel):
    """
    Credentials for a specific provider (Age-encrypted in vault).

    Examples
    --------
        LocalStack:
            aws_access_key_id: test
            aws_secret_access_key: test

        AWS:
            aws_access_key_id: "AKIA..."
            aws_secret_access_key: "..."
            aws_session_token: "..."  # Optional for temporary credentials

        DigitalOcean Spaces:
            aws_access_key_id: "DO..."
            aws_secret_access_key: "..."

    """

    # AWS-family credentials (LocalStack, AWS, DigitalOcean, MinIO)
    aws_access_key_id: str | None = None
    aws_secret_access_key: str | None = None
    aws_session_token: str | None = None  # Optional for temporary credentials

    # GCP credentials
    gcp_credentials_json: str | None = None
    gcp_project_id: str | None = None

    # Azure credentials
    azure_subscription_id: str | None = None
    azure_tenant_id: str | None = None
    azure_client_id: str | None = None
    azure_client_secret: str | None = None

    model_config = ConfigDict(extra="allow")  # Allow additional provider-specific credentials

    @model_validator(mode="after")
    def validate_at_least_one_credential(self) -> "ProviderCredentials":
        """Validate that at least one credential is provided."""
        has_aws = self.aws_access_key_id or self.aws_secret_access_key
        has_gcp = self.gcp_credentials_json or self.gcp_project_id
        has_azure = any([self.azure_subscription_id, self.azure_client_id, self.azure_client_secret])

        if not (has_aws or has_gcp or has_azure):
            raise ValueError("At least one set of credentials must be provided")

        return self


class CloudCredentials(BaseModel):
    """
    Cloud credentials file (vault/**/cloud-credentials.yaml).

    Example:
    -------
        providers:
          localstack:
            aws_access_key_id: test
            aws_secret_access_key: test
          aws-dev:
            aws_access_key_id: "AKIA..."
            aws_secret_access_key: "..."
        created: "2025-01-10"

    """

    providers: Annotated[
        dict[str, ProviderCredentials],
        Field(description="Credentials for each provider, keyed by provider name"),
    ]

    # Optional metadata
    description: str | None = None
    created: str | None = None
