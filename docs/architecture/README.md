# KStack-Lib Architecture

This section provides comprehensive documentation of kstack-lib's architecture, design patterns, and core concepts.

## Architecture Overview

KStack-lib is designed with a **context-aware architecture** that automatically adapts its behavior based on where code is running:

- **Local development** - Uses vault-based secrets, local configuration files
- **Kubernetes cluster** - Uses ConfigMaps, Secrets, and in-cluster service discovery

The architecture ensures that:

1. **Production code cannot accidentally run with dev secrets**
2. **Development code cannot accidentally access production resources**
3. **The right implementation is always selected** based on runtime context

## Core Concepts

### 1. Three-Tier Module Structure

```
kstack_lib/
├── any/          # Context-agnostic code (works anywhere)
├── local/        # Local-only code (dev machines, CI/CD)
└── cluster/      # Cluster-only code (K8s pods)
```

#### `any/` - Context-Agnostic Components

Contains code that works in **both** local and cluster contexts:

- **Protocols** - Abstract interfaces (no implementation details)
- **Types & Enums** - Data structures and constants
- **Exceptions** - Error types
- **IoC Container** - Dependency injection that auto-wires implementations
- **CAL Protocols** - Cloud Abstraction Layer interfaces

**Key files:**

- `any/protocols.py` - Protocol definitions
- `any/container.py` - IoC container with auto-wiring
- `any/context.py` - Runtime context detection
- `any/exceptions.py` - Exception hierarchy

#### `local/` - Local Development Components

Contains code for **local development only**:

- **Vault management** - Encrypted secrets with age/partsecrets
- **Local configuration** - Reads from filesystem
- **Development credentials** - Loads from vault files

**Import guards prevent usage in cluster:**

```python
# Every local/ module imports this guard
from kstack_lib.local._guards import _enforce_local
# Raises KStackEnvironmentError if imported in K8s pod
```

**Key files:**

- `local/security/vault.py` - Vault decryption and access
- `local/security/credentials.py` - Local credentials provider
- `local/config/environment.py` - Reads `.kstack.yaml`

#### `cluster/` - Cluster-Only Components

Contains code for **Kubernetes clusters only**:

- **ConfigMap access** - Reads K8s ConfigMaps
- **Secret access** - Reads K8s Secrets
- **Service discovery** - In-cluster DNS

**Import guards prevent usage locally:**

```python
# Every cluster/ module imports this guard
from kstack_lib.cluster._guards import _enforce_cluster
# Raises KStackEnvironmentError if imported outside K8s
```

**Key files:**

- `cluster/security/secrets.py` - K8s Secrets provider
- `cluster/config/environment.py` - Reads namespace from K8s

### 2. Inversion of Control (IoC) Container

**Purpose:** Automatically wire the correct implementation based on runtime context.

**Location:** `kstack_lib/any/container.py`

#### How It Works

```python
from kstack_lib.any.container import container

# Container auto-detects context and provides correct implementation
env_detector = container.environment_detector()
# Returns LocalEnvironmentDetector in local context
# Returns ClusterEnvironmentDetector in cluster context

secrets = container.secrets_provider()
# Returns LocalCredentialsProvider (uses vault) in local context
# Returns ClusterSecretsProvider (uses K8s Secrets) in cluster context
```

#### Architecture Pattern

```
┌─────────────────────────────────────────┐
│        Application Code                 │
│  (Imports from kstack_lib.any.*)        │
└──────────────┬──────────────────────────┘
               │
               ▼
┌─────────────────────────────────────────┐
│         IoC Container                    │
│  • Detects runtime context              │
│  • Selects implementation                │
│  • Manages singletons                    │
└──────────────┬──────────────────────────┘
               │
        ┌──────┴──────┐
        │             │
        ▼             ▼
┌─────────────┐ ┌──────────────┐
│   Local     │ │   Cluster    │
│ (Vault,     │ │ (ConfigMaps, │
│  .kstack)   │ │  Secrets)    │
└─────────────┘ └──────────────┘
```

#### Provider Pattern

Uses `dependency-injector` library's `Selector` provider:

```python
from dependency_injector import containers, providers

class KStackIoCContainer(containers.DeclarativeContainer):
    environment_detector = providers.Singleton(
        providers.Selector(
            _context_selector,  # Returns "cluster" or "local"
            cluster=providers.Factory(
                lambda: __import__("kstack_lib.cluster.config.environment",
                                   fromlist=["ClusterEnvironmentDetector"]).ClusterEnvironmentDetector()
            ),
            local=providers.Factory(
                lambda: __import__("kstack_lib.local.config.environment",
                                   fromlist=["LocalEnvironmentDetector"]).LocalEnvironmentDetector()
            ),
        )
    )
```

**Key features:**

- **Lazy loading** - Modules only imported when needed
- **Singleton pattern** - Same instance reused across application
- **Auto-wiring** - No manual configuration needed

### 3. Cloud Abstraction Layer (CAL)

**Purpose:** Provide unified interface for cloud services across providers (AWS, LocalStack, etc).

**Location:** `kstack_lib/cal/`

#### Architecture: Families and Providers

```
┌────────────────────────────────────────────────────┐
│          CloudProvider Protocol                     │
│  (Defines factory methods for services)            │
└───────────────────┬────────────────────────────────┘
                    │
        ┌───────────┴───────────┐
        │                       │
        ▼                       ▼
┌───────────────┐       ┌──────────────┐
│  AWS Family   │       │  Azure Family│
│  (aws, gov)   │       │  (Coming)    │
└───────┬───────┘       └──────────────┘
        │
        ▼
┌────────────────────────────────────────┐
│       Service Protocols                │
│  • ObjectStorage                       │
│  • Queue                               │
│  • SecretManager                       │
└────────────────────────────────────────┘
```

#### Provider Families

A **family** is a group of cloud providers that share the same SDK and implementation:

**AWS Family:**

- `aws` - Real AWS cloud
- `aws-gov` - AWS GovCloud
- `localstack` - LocalStack (AWS-compatible for dev/test)

All AWS family providers use:

- Same SDK: `boto3` / `aioboto3`
- Same adapter: `AWSFamilyProvider`
- Different credentials/endpoints

#### Service Protocols

Each service type has a protocol (interface):

```python
from typing import Protocol

class ObjectStorage(Protocol):
    """Protocol for object storage operations (S3-like)."""

    def list_buckets(self) -> list[str]: ...
    def create_bucket(self, bucket: str, region: str | None = None) -> None: ...
    def delete_bucket(self, bucket: str) -> None: ...
    def list_objects(self, bucket: str, prefix: str = "") -> list[ObjectStorageNode]: ...
    # ... more methods
```

Benefits:

- **Type safety** - MyPy verifies implementations
- **Contract enforcement** - All providers must implement all methods
- **Swappability** - Easy to switch providers

#### Usage Example

```python
from kstack_lib.cal import CloudContainer
from kstack_lib.config import ConfigMap
from kstack_lib.types import KStackLayer, KStackEnvironment

# Configure which cloud provider to use
cfg = ConfigMap(
    layer=KStackLayer.LAYER_3_GLOBAL_INFRA,
    environment=KStackEnvironment.DEVELOPMENT,
)

# Container automatically:
# 1. Loads cloud credentials from vault (local) or K8s (cluster)
# 2. Creates appropriate provider (LocalStack for dev, AWS for prod)
# 3. Provides typed service interfaces
with CloudContainer(cfg) as cloud:
    # Get object storage service (S3-compatible)
    storage = cloud.object_storage()

    # Use consistent API regardless of provider
    storage.create_bucket("my-bucket")
    storage.upload_object("my-bucket", "file.txt", b"content")

    # Get queue service (SQS-compatible)
    queue = cloud.queue()
    queue.send_message("my-queue", {"key": "value"})
```

### 4. Import Guards

**Purpose:** Prevent accidental misuse of context-specific code.

#### How Guards Work

Guards execute **at module import time**, before any code runs:

```python
# kstack_lib/local/_guards.py
from kstack_lib.any.context import is_in_cluster

_enforce_local = True  # Dummy symbol for import

if is_in_cluster():
    raise KStackEnvironmentError(
        "Cannot import local module inside Kubernetes cluster."
    )
```

Every module in `local/` or `cluster/` imports its guard:

```python
# kstack_lib/local/security/vault.py
from kstack_lib.local._guards import _enforce_local  # noqa: F401 - Import guard

# Rest of module code...
```

#### Benefits

1. **Fail-fast** - Errors caught at import time, not runtime
2. **Explicit** - Clear error messages guide developers
3. **Safety** - Impossible to accidentally use wrong implementation

#### Context Detection

```python
# kstack_lib/any/context.py
from pathlib import Path

def is_in_cluster() -> bool:
    """Detect if running inside Kubernetes cluster."""
    # Check for Kubernetes service account token
    token_file = Path("/var/run/secrets/kubernetes.io/serviceaccount/token")
    return token_file.exists()
```

## Design Patterns

### 1. Protocol-Based Design

All interfaces defined as Python `Protocol`:

```python
from typing import Protocol, runtime_checkable

@runtime_checkable
class SecretsProvider(Protocol):
    """Protocol for accessing secrets."""

    def get_secret(self, name: str, layer: str, env: str) -> dict[str, str]:
        """Get secret by name."""
        ...
```

**Benefits:**

- Structural typing (duck typing with type checks)
- No inheritance required
- Runtime checkability with `isinstance()`

### 2. Singleton Pattern

Services are singletons - created once, reused everywhere:

```python
# First call creates instance
detector1 = container.environment_detector()

# Subsequent calls return same instance
detector2 = container.environment_detector()

assert detector1 is detector2  # True
```

### 3. Factory Pattern

Container uses factories to defer creation until needed:

```python
# Not created until first access
secrets_provider = providers.Factory(
    lambda: __import__("kstack_lib.local.security.credentials",
                      fromlist=["LocalCredentialsProvider"]).LocalCredentialsProvider()
)
```

### 4. Lazy Loading

Modules only imported when actually used:

```python
# This import doesn't trigger cluster module loading
from kstack_lib.any.container import container

# Only NOW does cluster module load (if in cluster context)
detector = container.environment_detector()
```

## Testing Strategies

### Unit Tests

**Goal:** Test individual components in isolation.

**Pattern:** Mock context and dependencies:

```python
from unittest.mock import patch, MagicMock

def test_local_secrets_provider():
    # Mock environment detector
    mock_env = MagicMock()
    mock_env.get_environment.return_value = "development"

    # Mock vault
    with patch("kstack_lib.local.security.vault.KStackVault") as mock_vault:
        mock_vault.return_value.get_secret.return_value = {"key": "value"}

        provider = LocalCredentialsProvider(vault=mock_vault.return_value, environment="dev")
        creds = provider.get_credentials("s3", "layer3", "dev")

        assert creds["key"] == "value"
```

### Integration Tests

**Goal:** Test real cloud services (LocalStack).

**Pattern:** Use pytest fixtures with auto-start:

```python
@pytest.mark.integration
def test_s3_operations(localstack):  # Fixture auto-starts LocalStack
    from kstack_lib.cal import CloudContainer

    with CloudContainer(cfg) as cloud:
        storage = cloud.object_storage()
        storage.create_bucket("test-bucket")
        # ... test real operations
```

The `localstack` fixture (`tests/conftest.py`):

- Checks if Docker is available
- Starts LocalStack container automatically
- Waits for health check
- Cleans up after tests

### Testing Import Guards

**Challenge:** Guards run at module import time, before mocks apply.

**Solution:** Skip tests that require cluster modules:

```python
@pytest.mark.skip(
    reason="Import guards prevent testing cluster modules outside K8s. "
    "Guards run at module load time, before mocks can be applied."
)
def test_cluster_environment_detector(self):
    pass  # Would need subprocess-based testing or real K8s
```

## Backward Compatibility

### Compatibility Shims

Old code still works through re-exports:

```python
# kstack_lib/__init__.py
# OLD WAY (still works):
from kstack_lib import ConfigurationError, LayerAccessError

# NEW WAY (preferred):
from kstack_lib.any.exceptions import KStackConfigurationError, KStackLayerAccessError
```

### Lazy CAL Loading

CAL imports are lazy to avoid boto3 dependency issues:

```python
# kstack_lib/__init__.py
def __getattr__(name):
    """Lazy load CAL components only when accessed."""
    if name == "CloudContainer":
        from kstack_lib.cal import CloudContainer
        return CloudContainer
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
```

## Further Reading

- [IoC Container Deep Dive](./ioc-container.md) - Detailed container architecture
- [CAL Architecture](./cal-architecture.md) - Cloud Abstraction Layer internals
- [Testing Guide](../development/testing.md) - Comprehensive testing strategies
