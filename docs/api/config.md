# Configuration API Reference

Centralized configuration management for KStack applications.

## Overview

The configuration module provides a clean, unified API centered around the `ConfigMap` class. ConfigMap gives you access to:

- **Layer information** - Which layer you're in
- **Namespace information** - Kubernetes namespace
- **Routing information** - Active route/environment
- **Kubernetes detection** - Whether running in K8s

## ConfigMap Class

**The central object for all KStack configuration.**

ConfigMap is your main entry point. It provides layer info, namespace, routing, and K8s detection in one clean API.

::: kstack_lib.config.configmap.ConfigMap
options:
show_root_heading: true
show_source: true
members: - **init** - running_in_k8s - namespace - layer - get_active_route - set_active_route - get_value

### Understanding ConfigMap

Think of ConfigMap as your "configuration context". It knows:

1. **Where you are** - Which layer/namespace
2. **What environment** - Which route (dev/test/prod)
3. **How to access** - Kubernetes detection and access

### Creating a ConfigMap

#### Option 1: Explicit Layer (Local Development)

```python
from kstack_lib.config import ConfigMap
from kstack_lib.types import KStackLayer

# Specify layer explicitly
cfg = ConfigMap(layer=KStackLayer.LAYER_3_GLOBAL_INFRA)

print(cfg.namespace)      # 'layer-3-cloud'
print(cfg.layer)          # KStackLayer.LAYER_3_GLOBAL_INFRA
```

**When to use**: Running locally, in tests, or when you know the layer upfront.

#### Option 2: Auto-Detection (Kubernetes Deployment)

```python
from kstack_lib.config import ConfigMap

# Let ConfigMap detect the layer from the pod's namespace
if ConfigMap.running_in_k8s():
    cfg = ConfigMap()  # Auto-detects layer
    print(f"Detected: {cfg.layer.display_name}")
else:
    # Must specify layer when not in K8s
    cfg = ConfigMap(layer=KStackLayer.LAYER_3_GLOBAL_INFRA)
```

**When to use**: Running inside Kubernetes pods.

### Static Methods

#### `running_in_k8s()`

Check if currently running inside a Kubernetes pod.

```python
from kstack_lib.config import ConfigMap

if ConfigMap.running_in_k8s():
    print("Running in Kubernetes!")
    cfg = ConfigMap()  # Auto-detect
else:
    print("Running locally")
    cfg = ConfigMap(layer=KStackLayer.LAYER_3_GLOBAL_INFRA)
```

**Returns**: `bool` - `True` if in K8s, `False` otherwise

**How it works**: Checks for the service account namespace file that Kubernetes mounts in all pods.

### Properties

#### `namespace`

Get the Kubernetes namespace for this ConfigMap's layer.

```python
cfg = ConfigMap(layer=KStackLayer.LAYER_3_GLOBAL_INFRA)
print(cfg.namespace)  # 'layer-3-cloud'

cfg = ConfigMap(layer=KStackLayer.LAYER_2_GLOBAL_SERVICES)
print(cfg.namespace)  # 'layer-2-global'
```

**Returns**: `str` - Kubernetes namespace name

#### `layer`

Get the KStackLayer for this ConfigMap.

```python
cfg = ConfigMap(layer=KStackLayer.LAYER_3_GLOBAL_INFRA)
print(cfg.layer)                # KStackLayer.LAYER_3_GLOBAL_INFRA
print(cfg.layer.display_name)   # 'Layer 3: Global Infrastructure'
print(cfg.layer.number)         # 3
```

**Returns**: `KStackLayer` - The layer enum

### Methods

#### `get_active_route()`

Get the currently active route for this layer.

```python
cfg = ConfigMap(layer=KStackLayer.LAYER_3_GLOBAL_INFRA)
route = cfg.get_active_route()
print(route)  # 'development', 'testing', 'staging', etc.
```

**Returns**: `str` - Active route name

**Priority order**:

1. `KSTACK_ROUTE` environment variable (if set)
2. `kstack-route` ConfigMap in layer's namespace
3. Falls back to `'development'`

**Example with environment variable**:

```python
import os
os.environ['KSTACK_ROUTE'] = 'testing'

cfg = ConfigMap(layer=KStackLayer.LAYER_3_GLOBAL_INFRA)
print(cfg.get_active_route())  # 'testing'
```

#### `set_active_route(route_name)`

Set the active route for this layer.

```python
cfg = ConfigMap(layer=KStackLayer.LAYER_3_GLOBAL_INFRA)
cfg.set_active_route('testing')

# Verify the change
print(cfg.get_active_route())  # 'testing'
```

**Parameters**:

- `route_name` (`str`) - Route to activate (e.g., 'development', 'testing')

**Side effects**:

- Updates the `kstack-route` ConfigMap in Kubernetes
- Sets `KSTACK_ROUTE` environment variable for current process

**Raises**: `subprocess.CalledProcessError` if kubectl command fails

#### `get_value(configmap_name, key)`

Get a value from any ConfigMap in this layer's namespace.

```python
cfg = ConfigMap(layer=KStackLayer.LAYER_3_GLOBAL_INFRA)

# Get LocalStack instance
instance = cfg.get_value('localstack-proxy-config', 'active-instance')
print(instance)  # 'development'

# Get custom config
value = cfg.get_value('my-config', 'my-key')
```

**Parameters**:

- `configmap_name` (`str`) - Name of the ConfigMap
- `key` (`str`) - Key to retrieve from ConfigMap data

**Returns**: `Optional[str]` - Value for the key, or `None` if not found

## Secrets Management {#secrets-management}

### SecretsProvider Class

Unified secrets management across vault (local) and Kubernetes secrets (deployed).

::: kstack_lib.config.secrets.SecretsProvider
options:
show_root_heading: true
show_source: true
members: - **init** - get_current_environment - get_current_namespace - is_running_in_k8s - load_secrets - export_as_env_vars

### Understanding Secrets

KStack manages secrets in two modes:

1. **Local/Development** - Reads from vault YAML files
2. **Kubernetes** - Reads from K8s Secret resources

SecretsProvider automatically detects which mode to use.

### Creating a SecretsProvider

#### With ConfigMap (Recommended)

```python
from kstack_lib.config import ConfigMap, SecretsProvider
from kstack_lib.types import KStackLayer

# Create ConfigMap
cfg = ConfigMap(layer=KStackLayer.LAYER_3_GLOBAL_INFRA)

# Create SecretsProvider with ConfigMap
provider = SecretsProvider(config_map=cfg)
```

**Benefits**: SecretsProvider knows exactly which layer/namespace to use.

#### Auto-Detect (Simple)

```python
from kstack_lib.config import SecretsProvider

# SecretsProvider creates ConfigMap internally
provider = SecretsProvider()
```

**Note**: Auto-detection only works in Kubernetes. For local development, use the ConfigMap approach.

### Methods

#### `load_secrets(layer)`

Load secrets for a layer from the appropriate source.

```python
from kstack_lib.config import SecretsProvider

provider = SecretsProvider()
secrets = provider.load_secrets('layer3')

# Access secrets
print(secrets['redis-password'])
print(secrets['api-key'])
```

**Parameters**:

- `layer` (`LayerName`) - Layer name: 'layer0', 'layer1', 'layer2', or 'layer3'

**Returns**: `dict[str, str]` - Dictionary of secrets (key → value)

**Automatically**:

- Uses vault YAML files when running locally
- Uses K8s Secrets when running in Kubernetes

#### `export_as_env_vars(secrets)`

Export secrets as environment variables.

```python
provider = SecretsProvider()
secrets = provider.load_secrets('layer3')

# Export to environment
provider.export_as_env_vars(secrets)

# Now accessible via os.environ
import os
password = os.getenv('REDIS_PASSWORD')
```

**Parameters**:

- `secrets` (`dict[str, str]`) - Secrets dictionary
- `override_existing` (`bool`) - If `True`, override existing env vars. Default: `False`

**Key transformation**: Vault keys are converted to uppercase environment variables:

- `redis-password` → `REDIS_PASSWORD`
- `audit-redis-client-host` → `AUDIT_REDIS_CLIENT_HOST`

#### `is_running_in_k8s()`

Check if running in Kubernetes.

```python
provider = SecretsProvider()
if provider.is_running_in_k8s():
    print("Using K8s secrets")
else:
    print("Using vault files")
```

**Returns**: `bool` - `True` if in K8s, `False` otherwise

## Helper Functions

### `load_secrets_for_layer()`

**The easiest way to load secrets.** One-line function that loads and exports secrets.

::: kstack_lib.config.secrets.load_secrets_for_layer
options:
show_root_heading: true
show_source: true

#### Usage

```python
from kstack_lib.config import load_secrets_for_layer
from kstack_lib.types import KStackLayer

# Load secrets for Layer 0 and export as env vars
load_secrets_for_layer(
    layer=KStackLayer.LAYER_0_APPLICATIONS,
    auto_export=True
)

# Now secrets are in environment
import os
redis_host = os.getenv('REDIS_CLIENT_HOST')
redis_port = os.getenv('REDIS_CLIENT_PORT')
```

#### Parameters

- `layer` (`KStackLayer | str`) - Layer enum or string ('layer0', 'layer1', etc.)
- `auto_export` (`bool`) - If `True`, automatically export as env vars. Default: `True`
- `config_map` (`ConfigMap | None`) - Optional ConfigMap instance

#### Returns

`dict[str, str]` - Dictionary of secrets

#### Examples

**Using enum (recommended)**:

```python
from kstack_lib.types import KStackLayer

secrets = load_secrets_for_layer(
    layer=KStackLayer.LAYER_3_GLOBAL_INFRA,
    auto_export=True
)
```

**Using string (backward compatible)**:

```python
secrets = load_secrets_for_layer(
    layer='layer3',
    auto_export=True
)
```

**With explicit ConfigMap**:

```python
from kstack_lib.config import ConfigMap

cfg = ConfigMap(layer=KStackLayer.LAYER_3_GLOBAL_INFRA)
secrets = load_secrets_for_layer(
    layer=cfg.layer,
    config_map=cfg,
    auto_export=True
)
```

## Complete Examples

### Example 1: Application Initialization

```python
from kstack_lib.config import ConfigMap, load_secrets_for_layer
from kstack_lib.types import KStackLayer

def initialize_app():
    """Initialize application with KStack configuration."""

    # 1. Create ConfigMap
    if ConfigMap.running_in_k8s():
        cfg = ConfigMap()  # Auto-detect
    else:
        cfg = ConfigMap(layer=KStackLayer.LAYER_0_APPLICATIONS)

    print(f"Running in: {cfg.layer.display_name}")
    print(f"Namespace: {cfg.namespace}")
    print(f"Route: {cfg.get_active_route()}")

    # 2. Load secrets
    load_secrets_for_layer(
        layer=cfg.layer,
        config_map=cfg,
        auto_export=True
    )

    # 3. Secrets now available
    import os
    redis_host = os.getenv('REDIS_CLIENT_HOST')
    print(f"Redis: {redis_host}")

initialize_app()
```

### Example 2: Multi-Environment Configuration

```python
from kstack_lib.config import ConfigMap
from kstack_lib.types import KStackLayer

def get_app_config(layer: KStackLayer):
    """Get environment-specific configuration."""

    cfg = ConfigMap(layer=layer)
    route = cfg.get_active_route()

    # Route-specific configuration
    if route == 'development':
        return {
            'debug': True,
            'log_level': 'DEBUG',
            'workers': 1,
        }
    elif route == 'testing':
        return {
            'debug': True,
            'log_level': 'INFO',
            'workers': 2,
        }
    elif route == 'production':
        return {
            'debug': False,
            'log_level': 'WARNING',
            'workers': 4,
        }
    else:
        return {
            'debug': True,
            'log_level': 'INFO',
            'workers': 1,
        }

config = get_app_config(KStackLayer.LAYER_0_APPLICATIONS)
print(config)
```

### Example 3: Cross-Layer Access

```python
from kstack_lib.config import ConfigMap
from kstack_lib.types import KStackLayer

def audit_all_layers():
    """Check configuration across all layers."""

    layers = [
        KStackLayer.LAYER_0_APPLICATIONS,
        KStackLayer.LAYER_1_TENANT_INFRA,
        KStackLayer.LAYER_2_GLOBAL_SERVICES,
        KStackLayer.LAYER_3_GLOBAL_INFRA,
    ]

    for layer in layers:
        cfg = ConfigMap(layer=layer)

        print(f"\n{layer.display_name}")
        print(f"  Namespace: {cfg.namespace}")
        print(f"  Route: {cfg.get_active_route()}")

        # Get custom ConfigMap values if they exist
        custom_value = cfg.get_value('app-config', 'version')
        if custom_value:
            print(f"  Version: {custom_value}")

audit_all_layers()
```

### Example 4: Route Switching

```python
from kstack_lib.config import ConfigMap
from kstack_lib.types import KStackLayer

def switch_to_testing_route():
    """Switch all layers to testing route."""

    layers = [
        KStackLayer.LAYER_0_APPLICATIONS,
        KStackLayer.LAYER_1_TENANT_INFRA,
        KStackLayer.LAYER_2_GLOBAL_SERVICES,
        KStackLayer.LAYER_3_GLOBAL_INFRA,
    ]

    for layer in layers:
        cfg = ConfigMap(layer=layer)

        old_route = cfg.get_active_route()
        cfg.set_active_route('testing')
        new_route = cfg.get_active_route()

        print(f"{layer.display_name}: {old_route} → {new_route}")

switch_to_testing_route()
```

## Environment Variables

ConfigMap and SecretsProvider respect these environment variables:

| Variable           | Purpose                | Example                          | Priority |
| ------------------ | ---------------------- | -------------------------------- | -------- |
| `KSTACK_ROUTE`     | Override active route  | `KSTACK_ROUTE=testing`           | Highest  |
| `KSTACK_ENV`       | Environment name       | `KSTACK_ENV=dev`                 | -        |
| `KSTACK_VAULT_DIR` | Custom vault directory | `KSTACK_VAULT_DIR=/custom/vault` | High     |
| `KSTACK_ROOT`      | KStack root directory  | `KSTACK_ROOT=/opt/kstack`        | Medium   |

### Setting Environment Variables

```bash
# In shell
export KSTACK_ROUTE=testing
export KSTACK_ENV=dev

# In Python before importing
import os
os.environ['KSTACK_ROUTE'] = 'testing'
```

## Migration from Deprecated Functions

If you're using old detection functions, here's how to migrate:

### Old API (Deprecated)

```python
# OLD - Don't use this anymore
from kstack_lib.config import detect_current_namespace, detect_current_layer

namespace = detect_current_namespace()
layer = detect_current_layer()

if namespace:
    print(f"Namespace: {namespace}")
if layer:
    print(f"Layer: {layer.display_name}")
```

### New API (Recommended)

```python
# NEW - Use this instead
from kstack_lib.config import ConfigMap

if ConfigMap.running_in_k8s():
    cfg = ConfigMap()  # Auto-detect
    print(f"Namespace: {cfg.namespace}")
    print(f"Layer: {cfg.layer.display_name}")
else:
    print("Not running in Kubernetes")
```

**Benefits of new API**:

- ✅ All information in one object
- ✅ Cleaner, more intuitive
- ✅ Better type safety
- ✅ Easier to test and mock

## Best Practices

### ✅ DO: Use ConfigMap as Primary Interface

```python
from kstack_lib.config import ConfigMap
from kstack_lib.types import KStackLayer

cfg = ConfigMap(layer=KStackLayer.LAYER_3_GLOBAL_INFRA)
namespace = cfg.namespace
route = cfg.get_active_route()
```

### ✅ DO: Check running_in_k8s() Before Auto-Detection

```python
if ConfigMap.running_in_k8s():
    cfg = ConfigMap()  # Safe to auto-detect
else:
    cfg = ConfigMap(layer=KStackLayer.LAYER_3_GLOBAL_INFRA)
```

### ✅ DO: Pass ConfigMap to SecretsProvider

```python
cfg = ConfigMap(layer=KStackLayer.LAYER_3_GLOBAL_INFRA)
provider = SecretsProvider(config_map=cfg)
```

### ❌ DON'T: Use Deprecated Functions

```python
# Avoid these - they're deprecated
from kstack_lib.config import detect_current_namespace, detect_current_layer
```

### ✅ DO: Use Type Hints

```python
from kstack_lib.config import ConfigMap
from kstack_lib.types import KStackLayer

def configure(layer: KStackLayer) -> ConfigMap:
    """Type hints make code clearer and safer."""
    return ConfigMap(layer=layer)
```

## Troubleshooting

### ConfigMap auto-detection fails

**Problem**: `ValueError: Cannot auto-detect layer`

**Solution**: You're not running in Kubernetes. Specify layer explicitly:

```python
cfg = ConfigMap(layer=KStackLayer.LAYER_3_GLOBAL_INFRA)
```

### Secrets not loading

**Problem**: `load_secrets_for_layer()` returns empty dict

**Solutions**:

1. Check vault directory exists (`KSTACK_VAULT_DIR`)
2. Verify layer name is correct ('layer0', 'layer1', 'layer2', 'layer3')
3. Ensure YAML files exist in vault directory

### Environment variables not set

**Problem**: Secrets loaded but env vars not available

**Solution**: Make sure `auto_export=True`:

```python
load_secrets_for_layer(layer='layer3', auto_export=True)
```

### Route not changing

**Problem**: `set_active_route()` doesn't seem to work

**Solutions**:

1. Check kubectl access to cluster
2. Verify ConfigMap 'kstack-route' exists in namespace
3. Check `KSTACK_ROUTE` env var isn't overriding

## See Also

- [Types API](types.md) - KStackLayer and KStackRoute enums
- [Redis Configuration](redis.md) - Redis service discovery
- [LocalStack Configuration](localstack.md) - LocalStack service discovery
