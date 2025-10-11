# CAL Configuration Guide

This guide explains how to configure the Cloud Abstraction Layer (CAL), including configuration schemas, credential management, and examples.

## Overview

CAL configuration consists of three main components:

1. **Cloud Credentials** - Stored in encrypted vault (Age/partsecrets)
2. **Provider Configuration** - Defines cloud provider settings
3. **Environment Configuration** - Maps environments to providers

## Configuration File Locations

```
project/
├── config/                       # Configuration files
│   ├── environments/             # Environment configs
│   │   ├── development.yaml
│   │   ├── staging.yaml
│   │   └── production.yaml
│   └── providers/                # Provider configs
│       ├── localstack.yaml
│       ├── aws-dev.yaml
│       └── aws-prod.yaml
└── vault/                        # Encrypted credentials
    ├── dev/
    │   └── layer3/
    │       ├── secret.cloud-credentials.yaml  # Encrypted
    │       └── cloud-credentials.yaml         # Decrypted (gitignored)
    ├── staging/
    └── production/
```

## 1. Cloud Credentials (Vault)

### File Location

```
vault/{environment}/{layer}/cloud-credentials.yaml
```

**Example:** `vault/dev/layer3/cloud-credentials.yaml`

### Schema

```yaml
# Cloud credentials for all providers in this environment/layer
providers:
  # Provider name (must match provider config name)
  <provider-name>:
    # AWS-family credentials (AWS, LocalStack, DigitalOcean, MinIO)
    aws_access_key_id: string
    aws_secret_access_key: string
    aws_session_token: string # Optional, for temporary credentials

    # GCP credentials
    gcp_credentials_json: string
    gcp_project_id: string

    # Azure credentials
    azure_subscription_id: string
    azure_tenant_id: string
    azure_client_id: string
    azure_client_secret: string

# Optional metadata
description: string
created: string # ISO date
```

### Examples

#### LocalStack Development

```yaml
# vault/dev/layer3/cloud-credentials.yaml
providers:
  localstack:
    aws_access_key_id: "test"
    aws_secret_access_key: "test"

description: "LocalStack credentials for local development"
created: "2025-01-10"
```

#### AWS Development

```yaml
# vault/dev/layer3/cloud-credentials.yaml
providers:
  aws-dev:
    aws_access_key_id: "AKIAIOSFODNN7EXAMPLE"
    aws_secret_access_key: "wJalrXUtnFEMI/K7MDENG/bPxRfiCYEXAMPLEKEY"
    aws_session_token: "IQoJb3JpZ2luX2VjEJ..." # Optional

  localstack:
    aws_access_key_id: "test"
    aws_secret_access_key: "test"

description: "Development credentials for AWS and LocalStack"
created: "2025-01-10"
```

#### AWS Production (with IAM Role)

```yaml
# vault/production/layer3/cloud-credentials.yaml
providers:
  aws-prod:
    aws_access_key_id: "AKIAIOSFODNN7EXAMPLE"
    aws_secret_access_key: "wJalrXUtnFEMI/K7MDENG/bPxRfiCYEXAMPLEKEY"

description: "Production AWS credentials (IAM role with limited permissions)"
created: "2025-01-10"
```

#### Multi-Provider Setup

```yaml
# vault/dev/layer3/cloud-credentials.yaml
providers:
  localstack:
    aws_access_key_id: "test"
    aws_secret_access_key: "test"

  aws-dev:
    aws_access_key_id: "AKIA..."
    aws_secret_access_key: "..."

  digitalocean:
    aws_access_key_id: "DO00..." # DigitalOcean Spaces uses S3 API
    aws_secret_access_key: "..."

description: "Development credentials for multiple providers"
created: "2025-01-10"
```

### Encryption with Age/Partsecrets

Credentials are encrypted using Age:

```bash
# Encrypt credentials
uv run partsecrets hide --team dev

# This creates: vault/dev/layer3/secret.cloud-credentials.yaml (encrypted)
# Original file: vault/dev/layer3/cloud-credentials.yaml (deleted)

# Decrypt credentials (temporary)
uv run partsecrets reveal --team dev

# This creates: vault/dev/layer3/cloud-credentials.yaml (decrypted, gitignored)
# Encrypted file remains: vault/dev/layer3/secret.cloud-credentials.yaml
```

## 2. Provider Configuration

### File Location

```
config/providers/{provider-name}.yaml
```

**Example:** `config/providers/localstack.yaml`

### Schema

```yaml
# Unique provider name
name: string

# Provider family (which SDK to use)
provider_family: "aws" | "gcp" | "azure"

# Specific implementation
provider_implementation: "localstack" | "aws" | "digitalocean" | "minio" | "gcp" | "azure"

# Service-specific configuration
services:
  <service-name>:  # e.g., "s3", "sqs", "secretsmanager"
    endpoint_url: string  # Can use {{layer.namespace}} template
    presigned_url_domain: string | null

# Cloud region
region: string

# SSL verification
verify_ssl: boolean

# Optional metadata
description: string
created: string
notes: string
```

### Examples

#### LocalStack Provider

```yaml
# config/providers/localstack.yaml
name: localstack
provider_family: aws
provider_implementation: localstack

services:
  s3:
    # Template variables resolved at runtime
    endpoint_url: "http://localstack.{{layer.namespace}}.svc.cluster.local:4566"
    presigned_url_domain: "localstack.dev.partsnap.local"
  sqs:
    endpoint_url: "http://localstack.{{layer.namespace}}.svc.cluster.local:4566"
  secretsmanager:
    endpoint_url: "http://localstack.{{layer.namespace}}.svc.cluster.local:4566"

region: us-west-2
verify_ssl: false

description: "LocalStack for local development and testing"
created: "2025-01-10"
notes: |
  LocalStack runs in Kubernetes cluster
  presigned_url_domain used for external S3 access via Traefik
```

#### AWS Development Provider

```yaml
# config/providers/aws-dev.yaml
name: aws-dev
provider_family: aws
provider_implementation: aws

services:
  s3:
    # endpoint_url: null means use AWS defaults
    endpoint_url: null
    presigned_url_domain: null # Use AWS-generated URLs
  sqs:
    endpoint_url: null
  secretsmanager:
    endpoint_url: null

region: us-east-1
verify_ssl: true

description: "AWS development account"
created: "2025-01-10"
notes: |
  Development AWS account with limited permissions
  Uses IAM roles for access control
```

#### AWS Production Provider

```yaml
# config/providers/aws-prod.yaml
name: aws-prod
provider_family: aws
provider_implementation: aws

services:
  s3:
    endpoint_url: null
    presigned_url_domain: null
  sqs:
    endpoint_url: null
  secretsmanager:
    endpoint_url: null

region: us-west-2
verify_ssl: true

description: "AWS production account"
created: "2025-01-10"
notes: |
  Production AWS account
  Requires MFA for access
  Uses cross-account IAM roles
```

#### DigitalOcean Spaces Provider

```yaml
# config/providers/digitalocean.yaml
name: digitalocean
provider_family: aws # Uses S3-compatible API
provider_implementation: digitalocean

services:
  s3:
    endpoint_url: "https://nyc3.digitaloceanspaces.com"
    presigned_url_domain: "cdn.example.com" # CDN domain

region: nyc3 # DigitalOcean region
verify_ssl: true

description: "DigitalOcean Spaces for object storage"
created: "2025-01-10"
notes: |
  S3-compatible object storage
  Uses CDN for public assets
```

### Provider Family & Implementation Matrix

| Provider Family | Implementation | SDK          | Use Case              |
| --------------- | -------------- | ------------ | --------------------- |
| aws             | localstack     | boto3        | Local development     |
| aws             | aws            | boto3        | Real AWS cloud        |
| aws             | digitalocean   | boto3        | DigitalOcean Spaces   |
| aws             | minio          | boto3        | MinIO (on-premises)   |
| gcp             | gcp            | google-cloud | Google Cloud Platform |
| azure           | azure          | azure-sdk    | Microsoft Azure       |

## 3. Environment Configuration

### File Location

```
config/environments/{environment}.yaml
```

**Example:** `config/environments/development.yaml`

### Schema

```yaml
# Environment name
environment: "dev" | "testing" | "staging" | "production" | "data-collection" | "scratch"

# Deployment targets (which provider to use for each layer)
deployment_targets:
  layer3:  # Global infrastructure (Redis, LocalStack)
    provider: string  # References config/providers/{provider}.yaml
  layer1:  # Cloud services (S3, SQS, etc)
    provider: string

# Allow runtime provider override (for debugging)
allow_provider_override: boolean

# Optional metadata
description: string
created: string
```

### Examples

#### Development Environment

```yaml
# config/environments/development.yaml
environment: dev

deployment_targets:
  layer3:
    provider: localstack # References config/providers/localstack.yaml
  layer1:
    provider: localstack

allow_provider_override: true

description: "Local development environment using LocalStack"
created: "2025-01-10"
```

#### Staging Environment

```yaml
# config/environments/staging.yaml
environment: staging

deployment_targets:
  layer3:
    provider: aws-staging
  layer1:
    provider: aws-staging

allow_provider_override: true

description: "Staging environment on AWS"
created: "2025-01-10"
```

#### Production Environment

```yaml
# config/environments/production.yaml
environment: production

deployment_targets:
  layer3:
    provider: aws-prod
  layer1:
    provider: aws-prod

allow_provider_override: false # Never allow override in production!

description: "Production environment on AWS"
created: "2025-01-10"
```

#### Hybrid Environment

```yaml
# config/environments/hybrid.yaml
environment: dev

deployment_targets:
  layer3:
    provider: localstack # Local infrastructure
  layer1:
    provider: aws-dev # Real AWS for testing

allow_provider_override: true

description: "Hybrid environment (local infra, real AWS services)"
created: "2025-01-10"
```

## Configuration Loading

### How It Works

```python
from kstack_lib.cal import CloudContainer
from kstack_lib.config import ConfigMap
from kstack_lib.types import KStackLayer, KStackEnvironment
from pathlib import Path

# 1. Create ConfigMap (environment auto-detected from KSTACK_ROUTE)
cfg = ConfigMap(layer=KStackLayer.LAYER_3_GLOBAL_INFRA)

# 2. CloudContainer loads configuration
with CloudContainer(
    cfg=cfg,
    config_root=Path("/path/to/config"),
    vault_root=Path("/path/to/vault"),
) as cloud:
    # Configuration loading happens here:
    #
    # Step 1: Load environment config
    # → config/environments/development.yaml
    # → Finds: deployment_targets.layer3.provider = "localstack"
    #
    # Step 2: Load provider config
    # → config/providers/localstack.yaml
    # → Finds: endpoint_url template, region, etc.
    #
    # Step 3: Load credentials
    # → vault/dev/layer3/cloud-credentials.yaml
    # → Finds: localstack.aws_access_key_id, etc.
    #
    # Step 4: Create boto3 session with credentials
    #
    # Step 5: Create AWSFamilyProvider with session + endpoint
    #
    # Step 6: Return CloudContainer with provider

    # Now use services
    storage = cloud.object_storage()
```

### Template Variables

Provider configs support template variables:

**Available variables:**

- `{{layer.namespace}}` - Layer namespace (e.g., "layer-3-global-infra")
- `{{environment}}` - Environment name (e.g., "development")

**Example:**

```yaml
# config/providers/localstack.yaml
services:
  s3:
    endpoint_url: "http://localstack.{{layer.namespace}}.svc.cluster.local:4566"
    # Resolves to: http://localstack.layer-3-global-infra.svc.cluster.local:4566
```

## Complete Configuration Example

### Directory Structure

```
project/
├── config/
│   ├── environments/
│   │   ├── development.yaml
│   │   └── production.yaml
│   └── providers/
│       ├── localstack.yaml
│       └── aws-prod.yaml
└── vault/
    ├── dev/
    │   └── layer3/
    │       └── secret.cloud-credentials.yaml
    └── production/
        └── layer3/
            └── secret.cloud-credentials.yaml
```

### Development Configuration

**config/environments/development.yaml:**

```yaml
environment: dev
deployment_targets:
  layer3:
    provider: localstack
allow_provider_override: true
description: "Local development with LocalStack"
```

**config/providers/localstack.yaml:**

```yaml
name: localstack
provider_family: aws
provider_implementation: localstack
services:
  s3:
    endpoint_url: "http://localstack.{{layer.namespace}}.svc.cluster.local:4566"
    presigned_url_domain: "localstack.dev.partsnap.local"
region: us-west-2
verify_ssl: false
```

**vault/dev/layer3/cloud-credentials.yaml:**

```yaml
providers:
  localstack:
    aws_access_key_id: "test"
    aws_secret_access_key: "test"
```

### Production Configuration

**config/environments/production.yaml:**

```yaml
environment: production
deployment_targets:
  layer3:
    provider: aws-prod
allow_provider_override: false
description: "Production AWS environment"
```

**config/providers/aws-prod.yaml:**

```yaml
name: aws-prod
provider_family: aws
provider_implementation: aws
services:
  s3:
    endpoint_url: null
    presigned_url_domain: null
region: us-west-2
verify_ssl: true
```

**vault/production/layer3/cloud-credentials.yaml:**

```yaml
providers:
  aws-prod:
    aws_access_key_id: "AKIA..."
    aws_secret_access_key: "..."
```

## Configuration Validation

### Schema Validation

All configuration files are validated using Pydantic schemas:

```python
from kstack_lib.config.schemas import (
    CloudCredentials,
    ProviderConfig,
    EnvironmentConfig,
)

# Load and validate
creds = CloudCredentials.model_validate(yaml.safe_load(creds_file))
provider_cfg = ProviderConfig.model_validate(yaml.safe_load(provider_file))
env_cfg = EnvironmentConfig.model_validate(yaml.safe_load(env_file))
```

### Validation Rules

**Provider Configuration:**

- `provider_family` must match `provider_implementation`
  - AWS family: localstack, aws, digitalocean, minio
  - GCP family: gcp
  - Azure family: azure

**Environment Configuration:**

- Only `layer3` and `layer1` allowed in `deployment_targets`
- Provider must reference existing provider config

**Cloud Credentials:**

- Must provide at least one set of credentials (AWS, GCP, or Azure)
- AWS: `aws_access_key_id` and `aws_secret_access_key` required

## Best Practices

### 1. Separate Configs by Environment

**✅ Good:**

```
config/
├── environments/
│   ├── development.yaml
│   ├── staging.yaml
│   └── production.yaml
```

**❌ Bad:**

```
config/
└── config.yaml  # Single file for all environments
```

### 2. Use Meaningful Provider Names

**✅ Good:**

```yaml
providers:
  localstack: # Clear purpose
  aws-dev: # Environment indicated
  aws-prod: # Environment indicated
  digitalocean: # Provider type clear
```

**❌ Bad:**

```yaml
providers:
  provider1: # Not descriptive
  aws: # Which AWS account?
  temp: # Temporary? Delete it?
```

### 3. Never Commit Decrypted Credentials

**✅ Good (.gitignore):**

```gitignore
# Decrypted credentials (never commit!)
vault/**/cloud-credentials.yaml
vault/**/config.yaml

# Keep encrypted versions
!vault/**/secret.*.yaml
```

### 4. Use Template Variables

**✅ Good:**

```yaml
services:
  s3:
    endpoint_url: "http://localstack.{{layer.namespace}}.svc.cluster.local:4566"
    # Automatically resolves based on layer
```

**❌ Bad:**

```yaml
services:
  s3:
    endpoint_url: "http://localstack.layer-3-global-infra.svc.cluster.local:4566"
    # Hardcoded, breaks for other layers
```

### 5. Document Provider Configs

**✅ Good:**

```yaml
name: aws-prod
description: "Production AWS account"
notes: |
  Production account with the following:
  - MFA required for access
  - Cross-account IAM roles
  - CloudTrail logging enabled
  - Requires change approval
created: "2025-01-10"
```

## Troubleshooting

### Problem: "Provider not found"

**Error:**

```
KStackConfigurationError: Provider 'aws-dev' not found
```

**Solution:**

Check that `config/providers/aws-dev.yaml` exists and has `name: aws-dev`.

### Problem: "Credentials not found"

**Error:**

```
KStackServiceNotFoundError: Service 'localstack' not found in credentials file
```

**Solution:**

1. Decrypt vault: `uv run partsecrets reveal --team dev`
2. Check `vault/dev/layer3/cloud-credentials.yaml` has `providers.localstack`
3. Provider name must match exactly

### Problem: "Invalid provider family/implementation"

**Error:**

```
ValueError: Provider implementation 'gcp' not valid for family 'aws'
```

**Solution:**

Fix provider config:

```yaml
# Before (wrong)
provider_family: aws
provider_implementation: gcp

# After (correct)
provider_family: gcp
provider_implementation: gcp
```

### Problem: "Template variable not resolved"

**Error:**

```
endpoint_url still contains {{layer.namespace}}
```

**Solution:**

Ensure ConfigMap has correct layer:

```python
cfg = ConfigMap(
    layer=KStackLayer.LAYER_3_GLOBAL_INFRA,  # Must be set!
    # Environment auto-detected from KSTACK_ROUTE or ConfigMap
)
```

## Related Documentation

- [API Reference](./README.md) - Complete API documentation
- [CAL Architecture](../architecture/cal-architecture.md) - Design patterns
- [Testing Guide](../development/testing.md) - Testing with CAL
