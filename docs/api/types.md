# Types API Reference

Core type definitions and enumerations used throughout KStack.

## Overview

The types module (`kstack_lib.types`) provides clean, type-safe enumerations for layers and routes. Using these types instead of strings helps catch errors early and provides better IDE autocomplete.

## KStackLayer

Layer enumeration representing the 4-tier KStack architecture.

::: kstack_lib.any.types.layers.KStackLayer
options:
show_root_heading: true
show_source: true
members: - LAYER_0_APPLICATIONS - LAYER_1_TENANT_INFRA - LAYER_2_GLOBAL_SERVICES - LAYER_3_GLOBAL_INFRA - namespace - display_name - number - from_namespace - from_number - from_string

### Understanding Layers

Each layer serves a specific purpose in the architecture:

#### Layer 0: Applications

**Purpose**: User-facing applications and services
**Namespace**: `layer-0`
**Examples**: PartMaster, dashboards, web frontends
**Typical Usage**: Application deployment, user interfaces

```python
from kstack_lib.types import KStackLayer

layer = KStackLayer.LAYER_0_APPLICATIONS
print(layer.namespace)      # 'layer-0'
print(layer.display_name)   # 'Layer 0: Applications'
print(layer.number)         # 0
```

#### Layer 1: Tenant Infrastructure

**Purpose**: Per-customer/tenant infrastructure
**Namespace**: `layer-1`
**Examples**: Tenant-specific databases, caches, queues
**Typical Usage**: Multi-tenant resource isolation

```python
layer = KStackLayer.LAYER_1_TENANT_INFRA
print(layer.namespace)      # 'layer-1'
print(layer.display_name)   # 'Layer 1: Tenant Infrastructure'
```

#### Layer 2: Global Services

**Purpose**: Shared business logic services
**Namespace**: `layer-2-global`
**Examples**: PartFinder, analytics services, API gateways
**Typical Usage**: Cross-tenant shared services

```python
layer = KStackLayer.LAYER_2_GLOBAL_SERVICES
print(layer.namespace)      # 'layer-2-global'
print(layer.display_name)   # 'Layer 2: Global Services'
```

#### Layer 3: Global Infrastructure

**Purpose**: Foundation infrastructure components
**Namespace**: `layer-3-cloud`
**Examples**: Redis, LocalStack, message queues
**Typical Usage**: Infrastructure service deployment

```python
layer = KStackLayer.LAYER_3_GLOBAL_INFRA
print(layer.namespace)      # 'layer-3-cloud'
print(layer.display_name)   # 'Layer 3: Global Infrastructure'
```

### Properties

#### `namespace`

Returns the Kubernetes namespace for this layer.

```python
layer = KStackLayer.LAYER_3_GLOBAL_INFRA
namespace = layer.namespace  # 'layer-3-cloud'
```

#### `display_name`

Returns a human-readable display name.

```python
name = layer.display_name  # 'Layer 3: Global Infrastructure'
```

#### `number`

Returns the layer number (0-3).

```python
num = layer.number  # 3
```

### Class Methods

#### `from_namespace(namespace: str)`

Convert a Kubernetes namespace to a layer.

```python
layer = KStackLayer.from_namespace('layer-3-cloud')
# Returns: KStackLayer.LAYER_3_GLOBAL_INFRA
```

**Raises**: `ValueError` if namespace doesn't match any layer

#### `from_number(num: int)`

Get layer from number (0-3).

```python
layer = KStackLayer.from_number(3)
# Returns: KStackLayer.LAYER_3_GLOBAL_INFRA
```

**Raises**: `ValueError` if number is not 0-3

#### `from_string(value: str)`

Flexible string parsing supporting multiple formats.

```python
# Short aliases
layer = KStackLayer.from_string('layer0')   # LAYER_0_APPLICATIONS
layer = KStackLayer.from_string('layer3')   # LAYER_3_GLOBAL_INFRA

# Numbers
layer = KStackLayer.from_string('0')        # LAYER_0_APPLICATIONS
layer = KStackLayer.from_string('3')        # LAYER_3_GLOBAL_INFRA

# Full names
layer = KStackLayer.from_string('layer-0-applications')
layer = KStackLayer.from_string('layer-3-global-infra')
```

**Raises**: `ValueError` if value doesn't match any format

### Iteration

Iterate through all layers:

```python
from kstack_lib.types import KStackLayer

for layer in KStackLayer:
    print(f"{layer.display_name} → {layer.namespace}")

# Output:
# Layer 0: Applications → layer-0
# Layer 1: Tenant Infrastructure → layer-1
# Layer 2: Global Services → layer-2-global
# Layer 3: Global Infrastructure → layer-3-cloud
```

## KStackEnvironment

Environment enumeration representing different deployment environments.

::: kstack_lib.any.types.environments.KStackEnvironment
options:
show_root_heading: true
show_source: true
members: - DEVELOPMENT - STAGING - PRODUCTION - from_string

### Understanding Environments

Environments represent different deployment stages with varying security and stability requirements.

#### Available Environments

| Environment   | Purpose                | Typical Use Case                           |
| ------------- | ---------------------- | ------------------------------------------ |
| `DEVELOPMENT` | Local development      | Developer machines, rapid iteration        |
| `STAGING`     | Pre-production testing | QA testing, client demos, final validation |
| `PRODUCTION`  | Live production        | Customer-facing production systems         |

### Basic Usage

```python
from kstack_lib.types import KStackEnvironment

# Use enum values
env = KStackEnvironment.DEVELOPMENT
print(env.value)  # 'development'

# Check current environment
current_env = KStackEnvironment.DEVELOPMENT
if current_env == KStackEnvironment.DEVELOPMENT:
    print("Running in development mode")
```

### Class Methods

#### `from_string(value: str)`

Convert string to environment enum (case-insensitive).

```python
env = KStackEnvironment.from_string('development')  # KStackEnvironment.DEVELOPMENT
env = KStackEnvironment.from_string('STAGING')      # KStackEnvironment.STAGING
env = KStackEnvironment.from_string('production')   # KStackEnvironment.PRODUCTION
```

**Raises**: `ValueError` if value doesn't match any environment

### Iteration

```python
from kstack_lib.types import KStackEnvironment

# Print all environments
for env in KStackEnvironment:
    print(f"Environment: {env.value}")

# Output:
# Environment: development
# Environment: staging
# Environment: production
```

## LayerChoice

Extended layer enumeration for CLI commands, including "all" option.

::: kstack_lib.any.types.layers.LayerChoice
options:
show_root_heading: true
show_source: true

### Purpose

`LayerChoice` is used in CLI commands where you want to operate on a specific layer OR all layers at once.

### Values

- `ALL` - Operate on all layers
- `LAYER0` - Layer 0 only
- `LAYER1` - Layer 1 only
- `LAYER2` - Layer 2 only
- `LAYER3` - Layer 3 only

### Usage in CLI Commands

```python
from kstack_lib.types import LayerChoice, KStackLayer

def parse_layer(choice: LayerChoice) -> Optional[KStackLayer]:
    """Convert LayerChoice to KStackLayer, or None for 'all'."""
    if choice == LayerChoice.ALL:
        return None  # Indicates all layers
    return KStackLayer.from_string(choice.value)

# Example CLI usage
choice = LayerChoice.LAYER3
layer = parse_layer(choice)  # Returns KStackLayer.LAYER_3_GLOBAL_INFRA

choice = LayerChoice.ALL
layer = parse_layer(choice)  # Returns None
```

## Type Safety Benefits

Using enums instead of strings provides several benefits:

### 1. Compile-Time Checking

```python
# Good: Type-safe
from kstack_lib.types import KStackLayer
layer = KStackLayer.LAYER_3_GLOBAL_INFRA  # IDE knows this is valid

# Bad: Error-prone
layer = "layer-3-global-infra"  # Typos won't be caught
layer = "layer3-global"         # Wrong format, runtime error
```

### 2. IDE Autocomplete

Your IDE can suggest valid values when using enums:

```python
from kstack_lib.types import KStackEnvironment

env = KStackEnvironment.  # IDE shows: DEVELOPMENT, STAGING, PRODUCTION
```

### 3. Refactoring Safety

If layer names change, the enum changes in one place:

```python
# All code using KStackLayer.LAYER_3_GLOBAL_INFRA automatically updates
# If you used strings, you'd need to find and replace everywhere
```

## Examples

### Example 1: Layer Detection

```python
from kstack_lib.types import KStackLayer

def get_layer_from_env() -> KStackLayer:
    """Determine layer from environment variable."""
    import os
    layer_str = os.getenv('KSTACK_LAYER', 'layer3')
    return KStackLayer.from_string(layer_str)

layer = get_layer_from_env()
print(f"Running in: {layer.display_name}")
print(f"Namespace: {layer.namespace}")
```

### Example 2: Environment-Specific Configuration

```python
from kstack_lib.types import KStackEnvironment

def configure_for_environment(env: KStackEnvironment) -> dict:
    """Get environment-specific configuration."""
    if env == KStackEnvironment.DEVELOPMENT:
        return {
            'debug': True,
            'log_level': 'DEBUG',
            'cache_ttl': 60,
        }
    elif env == KStackEnvironment.PRODUCTION:
        return {
            'debug': False,
            'log_level': 'WARNING',
            'cache_ttl': 3600,
        }
    else:  # STAGING
        return {
            'debug': True,
            'log_level': 'INFO',
            'cache_ttl': 300,
        }

config = configure_for_environment(KStackEnvironment.DEVELOPMENT)
```

### Example 3: Multi-Layer Operations

```python
from kstack_lib.types import KStackLayer
from kstack_lib.config import ConfigMap

def check_all_layers():
    """Check status of all layers."""
    for layer in KStackLayer:
        cfg = ConfigMap(layer=layer)

        print(f"{layer.display_name}:")
        print(f"  Namespace: {cfg.namespace}")
        print(f"  Environment: {cfg.environment.value}")
        print()

check_all_layers()
```

## Best Practices

### ✅ DO: Use Enums

```python
from kstack_lib.types import KStackLayer, KStackEnvironment

layer = KStackLayer.LAYER_3_GLOBAL_INFRA
env = KStackEnvironment.DEVELOPMENT
```

### ❌ DON'T: Use Strings

```python
# Avoid this
layer = "layer-3-global-infra"
env = "development"
```

### ✅ DO: Use from_string() for User Input

```python
user_input = "layer3"
layer = KStackLayer.from_string(user_input)
```

### ✅ DO: Type Hint with Enums

```python
def deploy(layer: KStackLayer, env: KStackEnvironment) -> None:
    """Type hints provide safety and documentation."""
    pass
```
