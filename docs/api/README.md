# KStack-Lib API Reference

This section provides complete API documentation for kstack-lib's public interfaces.

## Quick Start

```python
# Import from kstack_lib.any for context-agnostic access
from kstack_lib.any import (
    # Container and DI
    container,
    get_environment_detector,
    get_secrets_provider,
    get_vault_manager,
    get_cloud_session_factory,

    # Types and Enums
    KStackLayer,
    KStackEnvironment,
    KStackRedisDatabase,

    # Exceptions
    KStackError,
    KStackConfigurationError,
    KStackServiceNotFoundError,

    # Utilities
    run_command,
)

# Import CAL
from kstack_lib.cal import CloudContainer

# Import configuration
from kstack_lib.config import ConfigMap
```

## Core Modules

### any/ - Context-Agnostic API

The `any/` module contains interfaces and utilities that work in both local and cluster contexts.

#### Container & Dependency Injection

**`container` (Global Singleton)**

```python
from kstack_lib.any.container import container

# Get services (auto-wired based on context)
env_detector = container.environment_detector()
secrets = container.secrets_provider()
vault = container.vault_manager()  # Local only
session_factory = container.cloud_session_factory()
```

**Helper Functions (Recommended)**

```python
from kstack_lib.any.container import (
    get_environment_detector,
    get_secrets_provider,
    get_vault_manager,
    get_cloud_session_factory,
)

# More convenient than using container directly
env = get_environment_detector()
secrets = get_secrets_provider()
```

#### Types and Enums

**KStackLayer**

```python
from kstack_lib.any.types import KStackLayer

# Available layers
KStackLayer.LAYER_0_APPLICATIONS      # Application layer
KStackLayer.LAYER_1_CLOUD_SERVICES    # Cloud services (S3, SQS, etc)
KStackLayer.LAYER_2_ROUTING           # Ingress/routing (Traefik)
KStackLayer.LAYER_3_GLOBAL_INFRA      # Global infrastructure (Redis, LocalStack)
```

**KStackEnvironment**

```python
from kstack_lib.any.types import KStackEnvironment

# Available environments
KStackEnvironment.DEVELOPMENT     # Local development
KStackEnvironment.TESTING         # Testing environment
KStackEnvironment.DATA_COLLECTION # Data collection environment
KStackEnvironment.SCRATCH         # Scratch/experimental
KStackEnvironment.STAGING         # Staging environment
KStackEnvironment.PRODUCTION      # Production environment
```

**KStackRedisDatabase**

```python
from kstack_lib.any.types import KStackRedisDatabase

# Available Redis databases
KStackRedisDatabase.PART_RAW      # Raw part data
KStackRedisDatabase.PART_CACHE    # Processed part cache
KStackRedisDatabase.AUDIT         # Audit logs
KStackRedisDatabase.SESSION       # User sessions
```

#### Exceptions

**Exception Hierarchy**

```python
from kstack_lib.any.exceptions import (
    KStackError,                    # Base exception
    KStackConfigurationError,       # Configuration issues
    KStackServiceNotFoundError,     # Service not available
    KStackLayerAccessError,         # Invalid layer access
    KStackEnvironmentError,         # Wrong context (local vs cluster)
    KStackRouteError,              # Invalid route
)

# Usage
try:
    config = load_config()
except KStackConfigurationError as e:
    print(f"Config error: {e}")
except KStackError as e:
    print(f"General error: {e}")
```

#### Utilities

**run_command()**

```python
from kstack_lib.any.utils import run_command

# Simple command
result = run_command(["kubectl", "get", "pods"])
print(result.stdout)

# With environment variables
result = run_command(
    ["partsecrets", "reveal"],
    env={"PARTSECRETS_VAULT_PATH": "/path/to/vault"}
)

# Don't raise on failure
result = run_command(["false"], check=False)
if result.returncode != 0:
    print(f"Command failed: {result.stderr}")

# With timeout
result = run_command(["sleep", "10"], timeout=5)  # Raises TimeoutExpired
```

### config/ - Configuration Management

**ConfigMap**

```python
from kstack_lib.config import ConfigMap
from kstack_lib.types import KStackLayer, KStackEnvironment

# Create configuration map (environment auto-detected from KSTACK_ROUTE)
cfg = ConfigMap(layer=KStackLayer.LAYER_3_GLOBAL_INFRA)

# Access properties
print(cfg.layer)         # KStackLayer.LAYER_3_GLOBAL_INFRA
print(cfg.environment)   # KStackEnvironment.DEVELOPMENT
print(cfg.namespace)     # "layer-3-global-infra"  # Auto-generated
```

**Configuration Loaders**

```python
from kstack_lib.config.loaders import (
    get_cloud_services_config,
    load_cloud_credentials,
)

# Load cloud services configuration
cloud_cfg = get_cloud_services_config(
    cfg=cfg,
    route="development",
    config_root=Path("/path/to/config"),
)

print(cloud_cfg.provider)      # "localstack" or "aws"
print(cloud_cfg.endpoint_url)  # "http://localhost:4566" for LocalStack
print(cloud_cfg.aws_region)    # "us-east-1"

# Load cloud credentials (from vault or K8s)
creds = load_cloud_credentials(
    environment="dev",
    layer="layer3",
    vault_dir=Path("/path/to/vault"),
)

print(creds["aws_access_key_id"])
print(creds["aws_secret_access_key"])
```

### cal/ - Cloud Abstraction Layer

**CloudContainer**

```python
from kstack_lib.cal import CloudContainer
from kstack_lib.config import ConfigMap
from kstack_lib.types import KStackLayer, KStackEnvironment
from pathlib import Path

# Create configuration (environment auto-detected from KSTACK_ROUTE)
cfg = ConfigMap(layer=KStackLayer.LAYER_3_GLOBAL_INFRA)

# Use as context manager
with CloudContainer(
    cfg=cfg,
    config_root=Path("/path/to/config"),
    vault_root=Path("/path/to/vault"),
) as cloud:
    # Get services
    storage = cloud.object_storage()
    queue = cloud.queue()
    secrets = cloud.secret_manager()

    # Use services
    storage.create_bucket("my-bucket")
    queue.send_message("my-queue", {"task": "process"})
```

**Service Interfaces**

**ObjectStorage**

```python
from kstack_lib.cal.protocols import ObjectStorage

storage: ObjectStorage = cloud.object_storage()

# Bucket operations
storage.create_bucket("my-bucket")
buckets = storage.list_buckets()
storage.delete_bucket("my-bucket")

# Object operations
storage.upload_object("my-bucket", "file.txt", b"content")
data = storage.download_object("my-bucket", "file.txt")
storage.delete_object("my-bucket", "file.txt")

# List objects
objects = storage.list_objects("my-bucket", prefix="uploads/")
for obj in objects:
    print(f"{obj.key}: {obj.size} bytes")

# Presigned URLs (temporary access)
url = storage.generate_presigned_url(
    "my-bucket",
    "file.txt",
    expires_in=3600,  # 1 hour
)
```

**Queue**

```python
from kstack_lib.cal.protocols import Queue

queue: Queue = cloud.queue()

# Queue operations
queue.create_queue("my-queue")
queues = queue.list_queues()
queue.delete_queue("my-queue")

# Message operations
queue.send_message("my-queue", {"task": "process", "id": 123})

messages = queue.receive_messages("my-queue", max_messages=10)
for msg in messages:
    print(f"Message: {msg.body}")
    # Process message...
    queue.delete_message("my-queue", msg.receipt_handle)

# Batch operations
queue.send_messages("my-queue", [
    {"task": "process", "id": 1},
    {"task": "process", "id": 2},
])
```

**SecretManager**

```python
from kstack_lib.cal.protocols import SecretManager

secrets: SecretManager = cloud.secret_manager()

# Create secret
secrets.create_secret("db-password", {"password": "secret123"})

# Retrieve secret
secret_value = secrets.get_secret_value("db-password")
print(secret_value["password"])

# Update secret
secrets.update_secret("db-password", {"password": "newsecret"})

# Delete secret
secrets.delete_secret("db-password")
```

## Dependency Injection Patterns

### Pattern 1: Direct Container Access

```python
from kstack_lib.any.container import container

# Get any service from global singleton
env = container.environment_detector()
secrets = container.secrets_provider()
```

**When to use:**

- Simple scripts
- Testing
- Direct access needed

### Pattern 2: Helper Functions (Recommended)

```python
from kstack_lib.any import (
    get_environment_detector,
    get_secrets_provider,
    get_vault_manager,
)

# More concise and readable
env = get_environment_detector()
secrets = get_secrets_provider()
vault = get_vault_manager()
```

**When to use:**

- Application code (preferred)
- Cleaner imports
- Standard use cases

### Pattern 3: Dependency Injection via **init**

```python
from kstack_lib.any import get_secrets_provider
from kstack_lib.any.protocols import SecretsProvider

class MyService:
    """Service with injected dependencies."""

    def __init__(self, secrets: SecretsProvider):
        self.secrets = secrets

    def get_api_key(self):
        creds = self.secrets.get_credentials("api", "layer3", "dev")
        return creds["api_key"]

# Inject dependency
secrets = get_secrets_provider()
service = MyService(secrets)
```

**When to use:**

- Class-based services
- Testability required
- Multiple dependencies

### Pattern 4: Factory Functions with DI

```python
from kstack_lib.any import get_cloud_session_factory
from kstack_lib.any.cloud_sessions import Boto3SessionFactory

def create_s3_client(factory: Boto3SessionFactory | None = None):
    """Create S3 client with optional factory injection."""
    if factory is None:
        factory = get_cloud_session_factory()

    session = factory.create_session("s3", "layer3", "dev")
    return session.client("s3")

# Use with default (DI from container)
s3 = create_s3_client()

# Use with custom factory (testing)
mock_factory = MockFactory()
s3 = create_s3_client(factory=mock_factory)
```

**When to use:**

- Optional dependency injection
- Testing with mocks
- Backward compatibility

## Testing Patterns

### Pattern 1: Mock Container Providers

```python
from unittest.mock import MagicMock
from kstack_lib.any.container import KStackIoCContainer

def test_my_service():
    # Create test container
    container = KStackIoCContainer()

    # Mock secrets provider
    mock_secrets = MagicMock()
    mock_secrets.get_credentials.return_value = {
        "api_key": "test_key"
    }
    container.secrets_provider.override(mock_secrets)

    # Use mocked container
    secrets = container.secrets_provider()
    creds = secrets.get_credentials("api", "layer3", "dev")
    assert creds["api_key"] == "test_key"
```

### Pattern 2: Inject Test Dependencies

```python
def test_my_service_with_injection():
    # Create mock directly
    mock_secrets = MagicMock()
    mock_secrets.get_credentials.return_value = {"api_key": "test"}

    # Inject into class
    service = MyService(secrets=mock_secrets)

    # Test
    api_key = service.get_api_key()
    assert api_key == "test"
    mock_secrets.get_credentials.assert_called_once()
```

### Pattern 3: Integration Tests with LocalStack

```python
import pytest
from kstack_lib.cal import CloudContainer

@pytest.mark.integration
def test_s3_operations(localstack):  # localstack fixture auto-starts
    cfg = ConfigMap(layer=KStackLayer.LAYER_3_GLOBAL_INFRA)

    with CloudContainer(cfg) as cloud:
        storage = cloud.object_storage()

        # Test against real LocalStack
        storage.create_bucket("test-bucket")
        storage.upload_object("test-bucket", "test.txt", b"content")
        data = storage.download_object("test-bucket", "test.txt")

        assert data == b"content"
```

## Best Practices

### 1. Always Use Container/DI

**✅ Good:**

```python
from kstack_lib.any import get_secrets_provider

secrets = get_secrets_provider()  # Auto-wired, context-aware
```

**❌ Bad:**

```python
from kstack_lib.local.security.credentials import LocalCredentialsProvider

secrets = LocalCredentialsProvider()  # Breaks in cluster!
```

### 2. Use Type Hints

**✅ Good:**

```python
from kstack_lib.any.protocols import SecretsProvider

def get_api_key(secrets: SecretsProvider) -> str:
    creds = secrets.get_credentials("api", "layer3", "dev")
    return creds["api_key"]
```

**❌ Bad:**

```python
def get_api_key(secrets):  # No type hints
    return secrets.get_credentials("api", "layer3", "dev")["api_key"]
```

### 3. Handle Exceptions

**✅ Good:**

```python
from kstack_lib.any.exceptions import (
    KStackConfigurationError,
    KStackServiceNotFoundError,
)

try:
    creds = secrets.get_credentials("api", "layer3", "dev")
except KStackServiceNotFoundError:
    print("Service not configured")
except KStackConfigurationError as e:
    print(f"Configuration error: {e}")
```

### 4. Use Context Managers for CAL

**✅ Good:**

```python
with CloudContainer(cfg) as cloud:
    storage = cloud.object_storage()
    storage.create_bucket("bucket")
    # Automatic cleanup on exit
```

**❌ Bad:**

```python
cloud = CloudContainer(cfg)
cloud.__enter__()  # Manual
storage = cloud.object_storage()
# Forgot to call __exit__!
```

## Related Documentation

- [IoC Container Deep Dive](../architecture/ioc-container.md) - Detailed container architecture
- [CAL Architecture](../architecture/cal-architecture.md) - Cloud Abstraction Layer internals
- [CAL Configuration](./cal-configuration.md) - Configuration schemas and examples
- [Types Reference](./types.md) - Complete type definitions
