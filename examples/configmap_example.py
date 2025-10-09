#!/usr/bin/env python3
"""
Example: Accessing ConfigMaps with the new clean API.

This example demonstrates the improved architecture where:
1. Layer definitions are semantic and clear
2. ConfigMap access is separated from Redis-specific code
3. Automatic namespace detection works when running in Kubernetes
"""

from kstack_lib.config import ConfigMap, KStackLayer

# Example 1: Explicit layer (use when running locally)
print("=== Example 1: Explicit Layer ===")
cfg = ConfigMap(layer=KStackLayer.LAYER_3_GLOBAL_INFRA)
print(f"ConfigMap: {cfg}")
print(f"Namespace: {cfg.layer.namespace}")
print(f"Display name: {cfg.layer.display_name}")

# Get active route
route = cfg.get_active_route()
print(f"Active route: {route}")

# Example 2: Auto-detection (works when running in Kubernetes pod)
print("\n=== Example 2: Auto-detection (in Kubernetes) ===")
try:
    cfg_auto = ConfigMap()  # No layer specified - auto-detects from namespace
    print(f"Detected layer: {cfg_auto.layer.display_name}")
    print(f"Namespace: {cfg_auto.layer.namespace}")
except ValueError as e:
    print(f"Not running in Kubernetes: {e}")

# Example 3: Different layers have different namespaces
print("\n=== Example 3: Multi-layer access ===")
for layer in KStackLayer:
    cfg_layer = ConfigMap(layer=layer)
    route = cfg_layer.get_active_route()
    print(f"{layer.display_name}:")
    print(f"  Namespace: {layer.namespace}")
    print(f"  Active route: {route}")

# Example 4: Read any ConfigMap value
print("\n=== Example 4: Read ConfigMap values ===")
cfg = ConfigMap(layer=KStackLayer.LAYER_3_GLOBAL_INFRA)

# Get active route from ConfigMap
route_value = cfg.get_value("kstack-route", "active-route")
print(f"Route from ConfigMap: {route_value or 'not set'}")

# Get LocalStack proxy config
localstack_instance = cfg.get_value("localstack-proxy-config", "active-instance")
print(f"LocalStack instance: {localstack_instance}")

# Example 5: Semantic layer naming
print("\n=== Example 5: Semantic layer names ===")
print(f"Layer 3 enum value: {KStackLayer.LAYER_3_GLOBAL_INFRA.value}")
print(f"Layer 3 namespace: {KStackLayer.LAYER_3_GLOBAL_INFRA.namespace}")
print(f"Layer 2 enum value: {KStackLayer.LAYER_2_GLOBAL_SERVICES.value}")
print(f"Layer 2 namespace: {KStackLayer.LAYER_2_GLOBAL_SERVICES.namespace}")

# Example 6: Reverse lookups
print("\n=== Example 6: Reverse lookups ===")
layer_from_ns = KStackLayer.from_namespace("layer-3-cloud")
print(f"from_namespace('layer-3-cloud'): {layer_from_ns.value}")

layer_from_num = KStackLayer.from_number(3)
print(f"from_number(3): {layer_from_num.value}")

print("\n✅ All examples completed!")
