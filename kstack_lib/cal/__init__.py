"""
KStack Cloud Abstraction Layer (CAL).

This module provides provider-agnostic abstractions for cloud services:
- Object Storage (S3-compatible)
- Message Queues (SQS-compatible)
- Secret Management
- Provider factory and dependency injection

The CAL enables applications to work with any cloud provider (LocalStack, AWS,
GCP, Azure, DigitalOcean, MinIO) through a unified interface.

Example:
-------
    >>> # Using the container (recommended)
    >>> from kstack_lib.cal import CloudContainer
    >>> from kstack_lib.config import ConfigMap, KStackLayer, KStackEnvironment
    >>>
    >>> cfg = ConfigMap(
    ...     layer=KStackLayer.LAYER_3_GLOBAL_INFRA,
    ...     environment=KStackEnvironment.DEVELOPMENT
    ... )
    >>>
    >>> with CloudContainer(cfg) as container:
    ...     storage = container.object_storage()
    ...     buckets = storage.list_buckets()
    ...     queue = container.queue()
    >>>
    >>> # Using the factory directly (for custom setups)
    >>> from kstack_lib.cal import create_cloud_provider
    >>> provider = create_cloud_provider(cfg)
    >>> storage = provider.create_object_storage()
    >>> storage.list_buckets()
    >>> provider.close()

"""

from kstack_lib.cal.container import CloudContainer
from kstack_lib.cal.factory import UnsupportedProviderError, create_cloud_provider
from kstack_lib.cal.ioc import CALIoCContainer, create_cal_container, get_cal_container, reset_cal_container
from kstack_lib.cal.protocols import (
    CloudProviderProtocol,
    ObjectStorageProtocol,
    QueueProtocol,
    SecretManagerProtocol,
)

__all__ = [
    "CloudProviderProtocol",
    "ObjectStorageProtocol",
    "QueueProtocol",
    "SecretManagerProtocol",
    "create_cloud_provider",
    "UnsupportedProviderError",
    "CloudContainer",
    "CALIoCContainer",
    "create_cal_container",
    "get_cal_container",
    "reset_cal_container",
]
