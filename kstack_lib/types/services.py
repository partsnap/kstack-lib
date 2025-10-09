"""
Service type definitions for KStack.

This module defines enums for services available in different layers.
"""

from enum import Enum


class KStackRedisDatabase(str, Enum):
    """
    Redis databases available in KStack.

    Each database serves a specific purpose in the PartSnap architecture.
    Redis databases are deployed in Layer 3 (Global Infrastructure).

    Attributes
    ----------
        PART_RAW: Raw part data storage
        PART_AUDIT: Audit log storage for part operations

    """

    PART_RAW = "part-raw"
    """Raw part data storage database."""

    PART_AUDIT = "part-audit"
    """Audit log storage database."""

    @property
    def display_name(self) -> str:
        """Get human-readable display name."""
        names = {
            self.PART_RAW: "Part Raw Data",
            self.PART_AUDIT: "Part Audit Logs",
        }
        return names[self]

    @property
    def layer(self) -> int:
        """Get the layer number where this service is deployed."""
        # All Redis databases are in Layer 3
        return 3


class KStackLocalStackService(str, Enum):
    """
    LocalStack services available in KStack.

    LocalStack provides AWS-compatible services for development and testing.
    LocalStack is deployed in Layer 3 (Global Infrastructure).

    Note: Currently there is only one LocalStack instance, but this enum
    provides consistency with other service types and allows for future expansion.

    """

    DEFAULT = "default"
    """Default LocalStack instance providing S3, SQS, DynamoDB, etc."""

    @property
    def display_name(self) -> str:
        """Get human-readable display name."""
        return "LocalStack (AWS Services)"

    @property
    def layer(self) -> int:
        """Get the layer number where this service is deployed."""
        # LocalStack is in Layer 3
        return 3
