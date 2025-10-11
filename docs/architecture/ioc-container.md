# IoC Container Deep Dive

## Overview

The **Inversion of Control (IoC) Container** is the heart of kstack-lib's context-aware architecture. It automatically wires the correct implementations based on runtime context (local vs cluster) without requiring manual configuration.

## Core Concept

**Traditional approach** (manual):

```python
# Developer must know context and choose implementation
if is_in_cluster():
    from kstack_lib.cluster.security import ClusterSecretsProvider
    secrets = ClusterSecretsProvider()
else:
    from kstack_lib.local.security import LocalCredentialsProvider
    secrets = LocalCredentialsProvider(vault, env)
```

**IoC Container approach** (automatic):

```python
# Container handles everything automatically
from kstack_lib.any.container import container
secrets = container.secrets_provider()
# Correct implementation chosen automatically!
```

## Container Implementation

### Location

`kstack_lib/any/container.py`

### Key Components

#### 1. Container Class

```python
from dependency_injector import containers, providers

class KStackIoCContainer(containers.DeclarativeContainer):
    """IoC container with auto-wiring based on runtime context."""

    # Providers defined as class attributes
    environment_detector = providers.Singleton(...)
    vault_manager = providers.Singleton(...)
    secrets_provider = providers.Singleton(...)
    cloud_session_factory = providers.Singleton(...)
```

Uses `dependency-injector` library's `DeclarativeContainer`:

- **Declarative** - Providers defined as class attributes
- **Type-safe** - Full MyPy support
- **Lazy** - Objects created on first access, not at import

#### 2. Context Selector

```python
def _context_selector() -> str:
    """Return 'cluster' or 'local' based on runtime context."""
    return "cluster" if is_in_cluster() else "local"
```

This function determines which implementation to use:

- Returns `"cluster"` when running in Kubernetes pod
- Returns `"local"` when running on dev machine or CI/CD

#### 3. Selector Provider

```python
environment_detector = providers.Singleton(
    providers.Selector(
        _context_selector,  # Callable that returns key
        cluster=providers.Factory(  # Implementation for "cluster" key
            lambda: __import__(
                "kstack_lib.cluster.config.environment",
                fromlist=["ClusterEnvironmentDetector"],
            ).ClusterEnvironmentDetector()
        ),
        local=providers.Factory(  # Implementation for "local" key
            lambda: __import__(
                "kstack_lib.local.config.environment",
                fromlist=["LocalEnvironmentDetector"],
            ).LocalEnvironmentDetector()
        ),
    )
)
```

**How Selector works:**

1. Calls `_context_selector()` to get key (`"cluster"` or `"local"`)
2. Looks up provider for that key
3. Calls provider's factory to create instance
4. Returns instance (cached for Singleton)

## Provider Types

### 1. Singleton

**Purpose:** Create once, reuse everywhere.

```python
environment_detector = providers.Singleton(
    providers.Selector(...)
)
```

**Behavior:**

```python
# First call creates instance
detector1 = container.environment_detector()

# Subsequent calls return SAME instance
detector2 = container.environment_detector()

assert detector1 is detector2  # True
```

**Why Singleton?**

- **Performance** - Avoid recreating expensive objects
- **Consistency** - Same configuration throughout application
- **State** - Maintain state across application

### 2. Factory

**Purpose:** Create fresh instance on each call (wrapped by Singleton above).

```python
providers.Factory(
    lambda: __import__("module", fromlist=["Class"]).Class()
)
```

**Why Lambda + **import**?**

- **Lazy loading** - Module not imported until first access
- **Guard safety** - Guards evaluated only when actually needed
- **Conditional** - Only import if this branch is selected

### 3. Callable

**Purpose:** Call function with injected dependencies.

```python
vault_manager = providers.Singleton(
    providers.Callable(
        lambda env_detector: __import__(
            "kstack_lib.local.security.vault",
            fromlist=["KStackVault"],
        ).KStackVault(environment=env_detector.get_environment()),
        env_detector=environment_detector,  # Dependency injection
    )
)
```

**How it works:**

1. `env_detector=environment_detector` injects environment detector
2. Lambda receives injected `env_detector` as parameter
3. Creates `KStackVault` with detected environment

## Complete Container Definition

```python
class KStackIoCContainer(containers.DeclarativeContainer):
    """IoC container for KStack - auto-wires adapters based on context."""

    # ========================================================================
    # Environment Detector - Detects current environment (dev, staging, prod)
    # ========================================================================
    environment_detector = providers.Singleton(
        providers.Selector(
            _context_selector,
            cluster=providers.Factory(
                lambda: __import__(
                    "kstack_lib.cluster.config.environment",
                    fromlist=["ClusterEnvironmentDetector"],
                ).ClusterEnvironmentDetector()
            ),
            local=providers.Factory(
                lambda: __import__(
                    "kstack_lib.local.config.environment",
                    fromlist=["LocalEnvironmentDetector"],
                ).LocalEnvironmentDetector()
            ),
        )
    )

    # ========================================================================
    # Vault Manager - LOCAL ONLY (raises error if accessed in cluster)
    # ========================================================================
    vault_manager = providers.Singleton(
        providers.Callable(
            lambda env_detector: __import__(
                "kstack_lib.local.security.vault",
                fromlist=["KStackVault"],
            ).KStackVault(environment=env_detector.get_environment()),
            env_detector=environment_detector,
        )
    )

    # ========================================================================
    # Secrets Provider - Different implementation per context
    # ========================================================================
    secrets_provider = providers.Singleton(
        providers.Selector(
            _context_selector,
            cluster=providers.Factory(
                lambda: __import__(
                    "kstack_lib.cluster.security.secrets",
                    fromlist=["ClusterSecretsProvider"],
                ).ClusterSecretsProvider()
            ),
            local=providers.Callable(
                lambda vault, env_detector: __import__(
                    "kstack_lib.local.security.credentials",
                    fromlist=["LocalCredentialsProvider"],
                ).LocalCredentialsProvider(
                    vault=vault, environment=env_detector.get_environment()
                ),
                vault=vault_manager,
                env_detector=environment_detector,
            ),
        )
    )

    # ========================================================================
    # Cloud Session Factory - Creates boto3/aioboto3 sessions
    # ========================================================================
    cloud_session_factory = providers.Singleton(
        providers.Callable(
            lambda secrets: __import__(
                "kstack_lib.any.cloud_sessions",
                fromlist=["Boto3SessionFactory"],
            ).Boto3SessionFactory(secrets_provider=secrets),
            secrets=secrets_provider,
        )
    )
```

## Dependency Graph

```
environment_detector (Singleton)
    ├─→ ClusterEnvironmentDetector (in cluster)
    └─→ LocalEnvironmentDetector (local)

vault_manager (Singleton, LOCAL ONLY)
    ├─→ Depends on: environment_detector
    └─→ KStackVault

secrets_provider (Singleton)
    ├─→ ClusterSecretsProvider (in cluster)
    └─→ LocalCredentialsProvider (local)
            ├─→ Depends on: vault_manager
            └─→ Depends on: environment_detector

cloud_session_factory (Singleton)
    ├─→ Depends on: secrets_provider
    └─→ Boto3SessionFactory
```

## Usage Patterns

### 1. Direct Container Access

```python
from kstack_lib.any.container import container

# Get services from global singleton container
env = container.environment_detector()
secrets = container.secrets_provider()
vault = container.vault_manager()  # Raises if in cluster
```

### 2. Helper Functions

```python
from kstack_lib.any.container import (
    get_environment_detector,
    get_secrets_provider,
    get_vault_manager,
    get_cloud_session_factory,
)

# More convenient, same singleton instance
env = get_environment_detector()
secrets = get_secrets_provider()
```

Helper functions defined in `container.py`:

```python
def get_environment_detector():
    """Get environment detector (singleton)."""
    return container.environment_detector()

def get_secrets_provider():
    """Get secrets provider (singleton)."""
    return container.secrets_provider()
```

### 3. Testing with Overrides

For unit tests, override providers with mocks:

```python
from unittest.mock import MagicMock
from kstack_lib.any.container import KStackIoCContainer

def test_something():
    # Create fresh container for testing
    test_container = KStackIoCContainer()

    # Override environment detector with mock
    mock_env = MagicMock()
    mock_env.get_environment.return_value = "testing"
    test_container.environment_detector.override(mock_env)

    # Use container with mocked dependencies
    secrets = test_container.secrets_provider()
    # ...
```

## Context Detection Details

### is_in_cluster() Implementation

```python
# kstack_lib/any/context.py
from pathlib import Path

def is_in_cluster() -> bool:
    """Detect if running inside Kubernetes cluster.

    Checks for Kubernetes service account token file which is
    automatically mounted into every pod.

    Returns:
        True if running in K8s pod, False otherwise
    """
    token_file = Path("/var/run/secrets/kubernetes.io/serviceaccount/token")
    return token_file.exists()
```

**How it works:**

- Kubernetes automatically mounts service account into every pod
- File exists at `/var/run/secrets/kubernetes.io/serviceaccount/token`
- On local machine, this path doesn't exist
- Simple, reliable, no configuration needed

### Context Selector

```python
def _context_selector() -> str:
    """Return 'cluster' or 'local' based on runtime context.

    Used by Selector providers to choose implementation.

    Returns:
        "cluster" if in K8s pod, "local" otherwise
    """
    return "cluster" if is_in_cluster() else "local"
```

**Why string keys?**

- `dependency-injector`'s `Selector` requires string keys
- Can't use boolean `True`/`False` (Python keyword args must be strings)
- Clear, self-documenting values

## Lazy Loading Mechanics

### Problem: Eager Imports Break Guards

**Naive approach (broken):**

```python
# This would break! Imports cluster module immediately
from kstack_lib.cluster.config.environment import ClusterEnvironmentDetector

environment_detector = providers.Singleton(
    providers.Selector(
        _context_selector,
        cluster=providers.Factory(ClusterEnvironmentDetector),  # Import guard fails!
        local=providers.Factory(LocalEnvironmentDetector),
    )
)
```

**Why it breaks:**

- `import` at top of file runs immediately
- Import guard in cluster module raises error BEFORE container even created
- Can't use container locally at all

### Solution: Lambda + **import**

```python
environment_detector = providers.Singleton(
    providers.Selector(
        _context_selector,
        cluster=providers.Factory(
            lambda: __import__(  # Import deferred until lambda called!
                "kstack_lib.cluster.config.environment",
                fromlist=["ClusterEnvironmentDetector"],
            ).ClusterEnvironmentDetector()
        ),
        ...
    )
)
```

**How it works:**

1. Lambda is created but not called (no import yet)
2. Container is instantiated (still no import)
3. `container.environment_detector()` called
4. Selector checks context → "local"
5. Skips cluster lambda (never called!)
6. Calls local lambda → imports local module only

**Benefits:**

- Only imports what's actually needed
- Guards only evaluated for used branch
- Works in both contexts

## Provider Override System

For testing, providers can be overridden:

```python
# Original implementation
container.environment_detector()  # Returns real detector

# Override with mock
mock = MagicMock()
container.environment_detector.override(mock)

# Now returns mock
container.environment_detector()  # Returns mock

# Reset to original
container.environment_detector.reset_override()
```

This is used extensively in tests:

```python
def test_secrets_provider_local(self):
    container = KStackIoCContainer()

    # Mock environment detector
    mock_env = MagicMock()
    mock_env.get_environment.return_value = "development"
    container.environment_detector.override(mock_env)

    # secrets_provider will use mocked environment
    provider = container.secrets_provider()
```

## Best Practices

### 1. Always Use Container

**Don't** import implementations directly:

```python
# BAD - bypasses container, breaks in wrong context
from kstack_lib.local.security.vault import KStackVault
vault = KStackVault()
```

**Do** use container:

```python
# GOOD - container handles context
from kstack_lib.any.container import get_vault_manager
vault = get_vault_manager()
```

### 2. Use Global Singleton

The global `container` instance ensures consistency:

```python
# Module A
from kstack_lib.any.container import container
secrets1 = container.secrets_provider()

# Module B (different file)
from kstack_lib.any.container import container
secrets2 = container.secrets_provider()

# Same instance!
assert secrets1 is secrets2
```

### 3. Mock in Tests

Create new container for each test to avoid state pollution:

```python
def test_something():
    # Fresh container per test
    container = KStackIoCContainer()

    # Override what you need
    container.environment_detector.override(mock_env)

    # Test...
```

### 4. Understand Dependency Order

Providers are evaluated lazily but dependencies must be available:

```python
# secrets_provider depends on vault_manager
# vault_manager must be defined BEFORE secrets_provider in container

vault_manager = providers.Singleton(...)  # Defined first

secrets_provider = providers.Singleton(
    providers.Callable(
        lambda vault: ...,
        vault=vault_manager,  # Reference to earlier provider
    )
)
```

## Troubleshooting

### Problem: Import Guard Fails When Creating Container

**Symptom:**

```
KStackEnvironmentError: Cannot import cluster module outside Kubernetes cluster
```

**Cause:** Eager import instead of lazy import

**Solution:** Use lambda + **import** pattern

### Problem: Wrong Implementation Selected

**Symptom:** Getting local implementation in cluster (or vice versa)

**Diagnosis:**

```python
from kstack_lib.any.context import is_in_cluster
print(f"In cluster: {is_in_cluster()}")
```

**Common causes:**

- Service account token not mounted
- Running in non-standard Kubernetes setup
- File path mocked incorrectly in tests

### Problem: Singleton Not Sharing State

**Symptom:** Different instances from same container

**Cause:** Creating multiple containers

**Solution:** Use global singleton:

```python
# GOOD
from kstack_lib.any.container import container
instance1 = container.secrets_provider()
instance2 = container.secrets_provider()
assert instance1 is instance2  # True

# BAD
from kstack_lib.any.container import KStackIoCContainer
container1 = KStackIoCContainer()
container2 = KStackIoCContainer()
instance1 = container1.secrets_provider()
instance2 = container2.secrets_provider()
assert instance1 is instance2  # False - different containers!
```

## Advanced Topics

### Custom Providers

You can extend the container for your own services:

```python
from kstack_lib.any.container import KStackIoCContainer
from dependency_injector import providers

class MyContainer(KStackIoCContainer):
    """Extended container with custom services."""

    my_service = providers.Singleton(
        providers.Callable(
            lambda secrets: MyService(secrets),
            secrets=KStackIoCContainer.secrets_provider,
        )
    )
```

### Multi-Container Patterns

For complex applications, use multiple containers:

```python
# Infrastructure container (kstack-lib)
from kstack_lib.any.container import container as infra_container

# Application container
class AppContainer(containers.DeclarativeContainer):
    # Wire in infrastructure services
    infra = providers.DependenciesContainer()

    # Application services
    user_service = providers.Singleton(
        lambda: UserService(db=infra.database)
    )
```

## Related Documentation

- [Architecture Overview](./README.md) - High-level architecture
- [CAL Architecture](./cal-architecture.md) - Cloud Abstraction Layer details
- [Testing Guide](../development/testing.md) - Testing with container
