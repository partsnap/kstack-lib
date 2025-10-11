# Cloud Abstraction Layer (CAL) Architecture

## Overview

The **Cloud Abstraction Layer (CAL)** provides a unified, protocol-based interface for cloud services across multiple providers (AWS, LocalStack, Azure, GCP, etc.). It enables writing cloud-agnostic code that works seamlessly across different cloud environments.

## Design Philosophy

### Goals

1. **Provider Independence** - Write once, run on any cloud
2. **Type Safety** - Full MyPy/Pyright support
3. **Testability** - Easy local testing with LocalStack
4. **Consistency** - Same API regardless of provider
5. **Performance** - Minimal overhead, direct SDK usage

### Non-Goals

- **Not a full abstraction** - Doesn't hide all provider differences
- **Not lowest common denominator** - Supports provider-specific features
- **Not ORM-like** - Thin wrapper, not hiding underlying SDK

## Architecture

### Three-Layer Design

```
┌─────────────────────────────────────────────────┐
│          Application Code                       │
│  (Uses CloudContainer, service protocols)       │
└────────────────────┬────────────────────────────┘
                     │
                     ▼
┌─────────────────────────────────────────────────┐
│          Service Protocols                      │
│  • ObjectStorage (S3-like)                      │
│  • Queue (SQS-like)                             │
│  • SecretManager (Secrets Manager-like)         │
│                                                  │
│  Protocol = interface (no implementation)       │
└────────────────────┬────────────────────────────┘
                     │
                     ▼
┌─────────────────────────────────────────────────┐
│          Provider Families                      │
│  • AWS Family (aws, aws-gov, localstack)        │
│  • Azure Family (azure, azure-gov)              │
│  • GCP Family (gcp)                             │
│                                                  │
│  Family = group sharing SDK/implementation      │
└────────────────────┬────────────────────────────┘
                     │
                     ▼
┌─────────────────────────────────────────────────┐
│          Cloud SDKs                             │
│  • boto3 / aioboto3 (AWS family)                │
│  • azure-sdk (Azure family)                     │
│  • google-cloud (GCP family)                    │
└─────────────────────────────────────────────────┘
```

## Provider Families

### Concept

A **family** is a group of cloud providers that:

- Share the same underlying SDK
- Share the same adapter implementation
- Differ only in credentials/endpoints

### AWS Family

**Members:**

- `aws` - Real AWS cloud (commercial)
- `aws-gov` - AWS GovCloud (US government)
- `localstack` - LocalStack (local development/testing)

**Shared:**

- SDK: `boto3` (sync) / `aioboto3` (async)
- Adapter: `AWSFamilyProvider`
- API compatibility: All implement AWS API

**Different:**

- Endpoints: Different URLs
- Credentials: Different access keys
- Regions: Different region codes

**Implementation:**

```python
# kstack_lib/cal/adapters/aws_family.py

class AWSFamilyProvider:
    """Adapter for AWS-compatible providers (aws, aws-gov, localstack)."""

    def __init__(
        self,
        session: boto3.Session,
        endpoint_url: str | None = None,  # Different per provider
    ):
        self.session = session
        self.endpoint_url = endpoint_url

    def create_object_storage(self) -> ObjectStorage:
        """Create S3-compatible object storage client."""
        return AWSObjectStorage(
            client=self.session.client('s3', endpoint_url=self.endpoint_url)
        )

    def create_queue(self) -> Queue:
        """Create SQS-compatible queue client."""
        return AWSQueue(
            client=self.session.client('sqs', endpoint_url=self.endpoint_url)
        )
```

### Future Families

**Azure Family** (planned):

- `azure` - Azure commercial cloud
- `azure-gov` - Azure Government
- SDK: `azure-sdk-for-python`
- Adapter: `AzureFamilyProvider`

**GCP Family** (planned):

- `gcp` - Google Cloud Platform
- SDK: `google-cloud-python`
- Adapter: `GCPFamilyProvider`

## Service Protocols

### Design Pattern

Each service type is defined as a Python `Protocol`:

```python
from typing import Protocol, runtime_checkable

@runtime_checkable
class ObjectStorage(Protocol):
    """Protocol for object storage operations (S3-like).

    Implementations:
    - AWSObjectStorage (AWS, LocalStack)
    - AzureBlobStorage (Azure) - future
    - GCSStorage (GCP) - future
    """

    def list_buckets(self) -> list[str]:
        """List all buckets."""
        ...

    def create_bucket(self, bucket: str, region: str | None = None) -> None:
        """Create a new bucket."""
        ...

    def delete_bucket(self, bucket: str) -> None:
        """Delete a bucket."""
        ...

    def list_objects(
        self,
        bucket: str,
        prefix: str = "",
        max_keys: int = 1000,
    ) -> list[ObjectStorageNode]:
        """List objects in bucket."""
        ...
```

**Benefits of Protocols:**

1. **Structural typing** - No inheritance required
2. **Type safety** - MyPy/Pyright verify implementations
3. **Runtime checks** - Can use `isinstance()` with `@runtime_checkable`
4. **Documentation** - Protocol is the API contract
5. **Flexibility** - Easy to add new implementations

### Available Services

#### 1. ObjectStorage

**Purpose:** S3-compatible object storage

**Operations:**

- Bucket management (list, create, delete)
- Object operations (upload, download, delete, list)
- Presigned URLs (time-limited access)
- Metadata operations

**Implementations:**

- `AWSObjectStorage` - AWS S3, LocalStack S3

**Example:**

```python
storage = cloud.object_storage()

# Bucket operations
storage.create_bucket("my-bucket")
buckets = storage.list_buckets()

# Object operations
storage.upload_object("my-bucket", "file.txt", b"content")
data = storage.download_object("my-bucket", "file.txt")

# Presigned URLs (temporary access)
url = storage.generate_presigned_url(
    "my-bucket", "file.txt", expires_in=3600
)
```

#### 2. Queue

**Purpose:** SQS-compatible message queuing

**Operations:**

- Queue management (create, delete, list)
- Message operations (send, receive, delete)
- Batch operations
- Queue attributes

**Implementations:**

- `AWSQueue` - AWS SQS, LocalStack SQS

**Example:**

```python
queue = cloud.queue()

# Create queue
queue.create_queue("my-queue")

# Send message
queue.send_message("my-queue", {"task": "process"})

# Receive messages
messages = queue.receive_messages("my-queue", max_messages=10)

# Delete message
queue.delete_message("my-queue", receipt_handle)
```

#### 3. SecretManager

**Purpose:** Secrets Manager-compatible secret storage

**Operations:**

- Secret management (create, get, update, delete)
- Secret rotation
- Versioning

**Implementations:**

- `AWSSecretManager` - AWS Secrets Manager, LocalStack

**Example:**

```python
secrets = cloud.secret_manager()

# Create secret
secrets.create_secret("db-password", {"password": "secret123"})

# Retrieve secret
secret_value = secrets.get_secret_value("db-password")

# Update secret
secrets.update_secret("db-password", {"password": "newsecret"})
```

## CloudContainer

### Purpose

**CloudContainer** is the main entry point to CAL. It:

1. Loads cloud credentials (from vault or K8s)
2. Creates appropriate provider (AWS/LocalStack/etc)
3. Provides typed service interfaces

### Location

`kstack_lib/cal/container.py`

### Usage Pattern

```python
from kstack_lib.cal import CloudContainer
from kstack_lib.config import ConfigMap
from kstack_lib.types import KStackLayer, KStackEnvironment

# Configure which cloud provider and environment
cfg = ConfigMap(
    layer=KStackLayer.LAYER_3_GLOBAL_INFRA,
    environment=KStackEnvironment.DEVELOPMENT,
)

# Context manager handles setup/teardown
with CloudContainer(cfg, config_root=Path("/path/to/config")) as cloud:
    # Get services
    storage = cloud.object_storage()
    queue = cloud.queue()
    secrets = cloud.secret_manager()

    # Use services
    storage.create_bucket("test-bucket")
```

### How It Works

```python
class CloudContainer:
    """Container for cloud service access."""

    def __init__(self, cfg: ConfigMap, config_root: Path, vault_root: Path):
        self.cfg = cfg
        self.config_root = config_root
        self.vault_root = vault_root
        self._provider: CloudProvider | None = None

    def __enter__(self) -> "CloudContainer":
        """Initialize provider on context entry."""
        # 1. Load cloud credentials
        creds = load_cloud_credentials(
            environment=self.cfg.environment,
            layer=self.cfg.layer,
            vault_dir=self.vault_root / "vault",
        )

        # 2. Determine provider from config
        cloud_cfg = get_cloud_services_config(
            self.cfg,
            route=self.cfg.route,
            config_root=self.config_root,
        )

        # 3. Create appropriate provider adapter
        if cloud_cfg.provider in ["aws", "aws-gov", "localstack"]:
            session = create_boto3_session(creds, cloud_cfg)
            self._provider = AWSFamilyProvider(session, cloud_cfg.endpoint_url)

        return self

    def object_storage(self) -> ObjectStorage:
        """Get object storage service."""
        return self._provider.create_object_storage()

    def queue(self) -> Queue:
        """Get queue service."""
        return self._provider.create_queue()
```

## Configuration

### Cloud Credentials

Stored in vault (local) or K8s Secrets (cluster):

```yaml
# vault/dev/layer3/cloud-credentials.yaml
providers:
  localstack:
    aws_access_key_id: "test"
    aws_secret_access_key: "test"

  aws-dev:
    aws_access_key_id: "AKIA..."
    aws_secret_access_key: "..."
    aws_session_token: "..." # optional
```

### Cloud Services Config

Defines which provider to use:

```yaml
# config/development/layer3/cloud-services.yaml
provider: localstack # or "aws", "aws-gov"
endpoint_url: "http://localhost:4566" # For LocalStack
aws_region: "us-east-1"
layer: layer-3-global-infra
route: development
```

### Provider Selection

```python
# Load config
cloud_cfg = get_cloud_services_config(cfg, route="development")

# cloud_cfg.provider determines which adapter to use
if cloud_cfg.provider == "localstack":
    # Use LocalStack endpoints
    provider = AWSFamilyProvider(session, endpoint_url="http://localhost:4566")
elif cloud_cfg.provider == "aws":
    # Use real AWS
    provider = AWSFamilyProvider(session, endpoint_url=None)
```

## Adding New Services

### 1. Define Protocol

```python
# kstack_lib/cal/protocols.py

from typing import Protocol

class Database(Protocol):
    """Protocol for database operations."""

    def execute_query(self, query: str) -> list[dict]: ...
    def execute_update(self, query: str) -> int: ...
```

### 2. Implement for AWS Family

```python
# kstack_lib/cal/adapters/aws_family.py

class AWSDatabase:
    """AWS RDS implementation."""

    def __init__(self, client):
        self.client = client

    def execute_query(self, query: str) -> list[dict]:
        # Implementation using boto3 RDS client
        ...

class AWSFamilyProvider:
    # Add method to create database service
    def create_database(self) -> Database:
        return AWSDatabase(self.session.client('rds'))
```

### 3. Add to CloudContainer

```python
# kstack_lib/cal/container.py

class CloudContainer:
    def database(self) -> Database:
        """Get database service."""
        return self._provider.create_database()
```

### 4. Add to CloudProvider Protocol

```python
# kstack_lib/cal/protocols.py

class CloudProvider(Protocol):
    """Protocol for cloud provider factories."""

    def create_object_storage(self) -> ObjectStorage: ...
    def create_queue(self) -> Queue: ...
    def create_secret_manager(self) -> SecretManager: ...
    def create_database(self) -> Database: ...  # New!
```

## Adding New Provider Families

### Example: Adding Azure Family

#### 1. Create Azure Adapter

```python
# kstack_lib/cal/adapters/azure_family.py

from azure.storage.blob import BlobServiceClient
from kstack_lib.cal.protocols import CloudProvider, ObjectStorage

class AzureBlobStorage:
    """Azure Blob Storage implementation of ObjectStorage protocol."""

    def __init__(self, client: BlobServiceClient):
        self.client = client

    def list_buckets(self) -> list[str]:
        return [container.name for container in self.client.list_containers()]

    def create_bucket(self, bucket: str, region: str | None = None) -> None:
        self.client.create_container(bucket)

    # ... implement all ObjectStorage methods

class AzureFamilyProvider:
    """Provider for Azure-compatible clouds."""

    def __init__(self, connection_string: str):
        self.connection_string = connection_string

    def create_object_storage(self) -> ObjectStorage:
        client = BlobServiceClient.from_connection_string(self.connection_string)
        return AzureBlobStorage(client)

    # ... implement all CloudProvider methods
```

#### 2. Update CloudContainer

```python
# kstack_lib/cal/container.py

def __enter__(self) -> "CloudContainer":
    cloud_cfg = get_cloud_services_config(self.cfg)

    if cloud_cfg.provider in ["aws", "aws-gov", "localstack"]:
        # AWS family
        self._provider = AWSFamilyProvider(...)

    elif cloud_cfg.provider in ["azure", "azure-gov"]:
        # Azure family
        from kstack_lib.cal.adapters.azure_family import AzureFamilyProvider
        self._provider = AzureFamilyProvider(...)

    return self
```

#### 3. Add Configuration Support

```yaml
# config/development/layer3/cloud-services.yaml
provider: azure
connection_string: "..."
# Azure-specific settings
```

## Testing Strategies

### Unit Tests

Test adapters with mocked SDK clients:

```python
from unittest.mock import MagicMock
from kstack_lib.cal.adapters.aws_family import AWSObjectStorage

def test_create_bucket():
    # Mock boto3 S3 client
    mock_client = MagicMock()
    storage = AWSObjectStorage(mock_client)

    # Test
    storage.create_bucket("test-bucket")

    # Verify SDK called correctly
    mock_client.create_bucket.assert_called_once_with(
        Bucket="test-bucket"
    )
```

### Integration Tests

Test with real LocalStack:

```python
@pytest.mark.integration
def test_s3_operations(localstack):  # Auto-starts LocalStack
    from kstack_lib.cal import CloudContainer

    cfg = ConfigMap(
        layer=KStackLayer.LAYER_3_GLOBAL_INFRA,
        environment=KStackEnvironment.DEVELOPMENT,
    )

    with CloudContainer(cfg) as cloud:
        storage = cloud.object_storage()

        # Test against real LocalStack
        storage.create_bucket("integration-test")
        buckets = storage.list_buckets()
        assert "integration-test" in buckets
```

### Protocol Conformance Tests

Verify implementations match protocols:

```python
from kstack_lib.cal.protocols import ObjectStorage
from kstack_lib.cal.adapters.aws_family import AWSObjectStorage

def test_aws_object_storage_conforms_to_protocol():
    """Verify AWSObjectStorage implements ObjectStorage protocol."""
    mock_client = MagicMock()
    storage = AWSObjectStorage(mock_client)

    # Runtime protocol check
    assert isinstance(storage, ObjectStorage)
```

## Best Practices

### 1. Always Use Protocols

Define interfaces as protocols, not base classes:

```python
# GOOD - Protocol (structural typing)
class ObjectStorage(Protocol):
    def create_bucket(self, bucket: str) -> None: ...

# BAD - ABC (inheritance required)
from abc import ABC, abstractmethod

class ObjectStorage(ABC):
    @abstractmethod
    def create_bucket(self, bucket: str) -> None: ...
```

### 2. Keep Adapters Thin

Adapters should be thin wrappers, not hide SDK:

```python
# GOOD - Simple wrapper
def create_bucket(self, bucket: str, region: str | None = None) -> None:
    kwargs = {"Bucket": bucket}
    if region:
        kwargs["CreateBucketConfiguration"] = {"LocationConstraint": region}
    self.client.create_bucket(**kwargs)

# BAD - Too much logic
def create_bucket(self, bucket: str, region: str | None = None) -> None:
    # Lots of custom logic
    # Hiding SDK behavior
    # Hard to debug
```

### 3. Use CloudContainer

Always use CloudContainer, not adapters directly:

```python
# GOOD
with CloudContainer(cfg) as cloud:
    storage = cloud.object_storage()

# BAD - Bypasses credential loading
from kstack_lib.cal.adapters.aws_family import AWSFamilyProvider
provider = AWSFamilyProvider(...)  # Where do credentials come from?
```

### 4. Type Hints Everywhere

Full type hints for IDE support and type checking:

```python
def list_objects(
    self,
    bucket: str,
    prefix: str = "",
    max_keys: int = 1000,
) -> list[ObjectStorageNode]:
    """List objects with full type hints."""
    ...
```

## Async Support (Future)

CAL will support async operations with `aioboto3`:

```python
class AsyncObjectStorage(Protocol):
    """Async version of ObjectStorage protocol."""

    async def create_bucket(self, bucket: str) -> None: ...
    async def upload_object(self, bucket: str, key: str, data: bytes) -> None: ...

class AsyncCloudContainer:
    """Async version of CloudContainer."""

    async def __aenter__(self) -> "AsyncCloudContainer":
        # Initialize async provider
        ...

    def async_object_storage(self) -> AsyncObjectStorage:
        return self._provider.create_async_object_storage()

# Usage
async with AsyncCloudContainer(cfg) as cloud:
    storage = cloud.async_object_storage()
    await storage.create_bucket("async-bucket")
```

## Related Documentation

- [Architecture Overview](./README.md)
- [IoC Container](./ioc-container.md)
- [Testing Guide](../development/testing.md)
