# kstack-lib Examples

This directory contains working examples demonstrating how to use the kstack-lib library.

## Available Examples

### ConfigMap Example (`configmap_example.py`)

Demonstrates the new ConfigMap and KStackLayer architecture:

- Using the KStackLayer enum with semantic naming
- Accessing ConfigMaps with explicit layer specification
- Auto-detection when running in Kubernetes
- Reading ConfigMap values across different layers
- Reverse lookups (namespace to layer, number to layer)

**Run it:**

```bash
KSTACK_ROUTE=development python examples/configmap_example.py
```

**Key Features Demonstrated:**

- ✅ Semantic layer naming (`layer-3-global-infra` instead of `layer-3`)
- ✅ Clean separation of ConfigMap logic from Redis-specific code
- ✅ Namespace abstraction via layer enum
- ✅ Auto-detection when running in Kubernetes pods

## Usage

All examples can be run directly from the kstack-lib root directory:

```bash
# Set the active route
export KSTACK_ROUTE=development

# Run an example
python examples/configmap_example.py
```

## See Also

- [API Documentation](../docs/api/config.md) - Full API reference with inline examples
- [Configuration Guide](../docs/api/config.md#layer-and-configmap-management) - Detailed usage patterns
