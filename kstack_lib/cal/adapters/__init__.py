"""
Cloud service adapters for different providers.

This module contains provider-specific implementations of the cloud service protocols:

- aws_family: AWS, LocalStack, DigitalOcean Spaces, MinIO (boto3-based)
- Future: gcp_family, azure_family, etc.
"""

from kstack_lib.cal.adapters.aws_family import (
    AWSFamilyProvider,
    AWSObjectStorage,
    AWSQueue,
    AWSSecretManager,
)

__all__ = [
    "AWSFamilyProvider",
    "AWSObjectStorage",
    "AWSQueue",
    "AWSSecretManager",
]
