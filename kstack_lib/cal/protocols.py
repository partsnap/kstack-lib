"""
Cloud Abstraction Layer Protocol Definitions.

This module defines protocols (structural typing) for cloud service abstractions.
Protocols allow any provider implementation that matches the interface to be used,
enabling true provider independence.

Key protocols:
- ObjectStorageProtocol: S3-compatible object storage
- QueueProtocol: SQS-compatible message queues
- SecretManagerProtocol: Secrets management (AWS Secrets Manager, etc.)
- CloudProviderProtocol: Factory interface for creating service clients
"""

from pathlib import Path
from typing import Any, BinaryIO, Protocol, runtime_checkable


@runtime_checkable
class ObjectStorageProtocol(Protocol):
    """
    Protocol for S3-compatible object storage operations.

    This protocol defines the interface for object storage operations that work
    across all S3-compatible providers (AWS S3, LocalStack, DigitalOcean Spaces,
    MinIO, Google Cloud Storage with S3 interoperability, etc.).

    All implementations must support:
    - Bucket operations (list, create, delete)
    - Object operations (upload, download, delete, list)
    - Presigned URL generation
    - Metadata management
    """

    def list_buckets(self) -> list[str]:
        """
        List all buckets in the object storage.

        Returns
        -------
            List of bucket names

        """
        ...

    def create_bucket(self, bucket_name: str) -> None:
        """
        Create a new bucket.

        Args:
        ----
            bucket_name: Name of the bucket to create

        Raises:
        ------
            Exception: If bucket creation fails

        """
        ...

    def delete_bucket(self, bucket_name: str) -> None:
        """
        Delete a bucket (must be empty).

        Args:
        ----
            bucket_name: Name of the bucket to delete

        Raises:
        ------
            Exception: If bucket deletion fails or bucket is not empty

        """
        ...

    def list_objects(self, bucket_name: str, prefix: str = "") -> list[dict[str, Any]]:
        """
        List objects in a bucket with optional prefix filtering.

        Args:
        ----
            bucket_name: Name of the bucket
            prefix: Prefix to filter objects (e.g., "folder/subfolder/")

        Returns:
        -------
            List of object metadata dictionaries with keys:
            - Key: object key (path)
            - Size: object size in bytes
            - LastModified: last modification timestamp
            - ETag: entity tag for object version

        """
        ...

    def upload_object(
        self,
        bucket_name: str,
        object_key: str,
        file_path: Path | None = None,
        file_obj: BinaryIO | None = None,
        content_type: str | None = None,
        metadata: dict[str, str] | None = None,
    ) -> None:
        """
        Upload an object to the bucket.

        Args:
        ----
            bucket_name: Name of the bucket
            object_key: Key (path) for the object
            file_path: Path to file to upload (mutually exclusive with file_obj)
            file_obj: File-like object to upload (mutually exclusive with file_path)
            content_type: MIME type of the object (auto-detected if None)
            metadata: Custom metadata key-value pairs

        Raises:
        ------
            ValueError: If neither file_path nor file_obj provided, or both provided
            Exception: If upload fails

        """
        ...

    def download_object(
        self,
        bucket_name: str,
        object_key: str,
        file_path: Path | None = None,
    ) -> bytes | None:
        """
        Download an object from the bucket.

        Args:
        ----
            bucket_name: Name of the bucket
            object_key: Key (path) of the object
            file_path: Optional path to save the file to

        Returns:
        -------
            Object bytes if file_path is None, otherwise None (saves to file)

        Raises:
        ------
            Exception: If download fails or object not found

        """
        ...

    def delete_object(self, bucket_name: str, object_key: str) -> None:
        """
        Delete an object from the bucket.

        Args:
        ----
            bucket_name: Name of the bucket
            object_key: Key (path) of the object to delete

        Raises:
        ------
            Exception: If deletion fails

        """
        ...

    def generate_presigned_url(
        self,
        bucket_name: str,
        object_key: str,
        expiration: int = 3600,
        http_method: str = "GET",
    ) -> str:
        """
        Generate a presigned URL for temporary access to an object.

        Args:
        ----
            bucket_name: Name of the bucket
            object_key: Key (path) of the object
            expiration: URL expiration time in seconds (default: 1 hour)
            http_method: HTTP method for the URL (GET, PUT, etc.)

        Returns:
        -------
            Presigned URL string

        Raises:
        ------
            Exception: If URL generation fails

        """
        ...

    def get_object_metadata(self, bucket_name: str, object_key: str) -> dict[str, Any]:
        """
        Get metadata for an object.

        Args:
        ----
            bucket_name: Name of the bucket
            object_key: Key (path) of the object

        Returns:
        -------
            Dictionary with metadata including:
            - ContentLength: size in bytes
            - ContentType: MIME type
            - LastModified: timestamp
            - Metadata: custom metadata dict
            - ETag: entity tag

        Raises:
        ------
            Exception: If object not found

        """
        ...


@runtime_checkable
class QueueProtocol(Protocol):
    """
    Protocol for SQS-compatible message queue operations.

    This protocol defines the interface for message queue operations that work
    across all SQS-compatible providers (AWS SQS, LocalStack, etc.).
    """

    def create_queue(self, queue_name: str, attributes: dict[str, str] | None = None) -> str:
        """
        Create a new queue.

        Args:
        ----
            queue_name: Name of the queue
            attributes: Optional queue attributes (e.g., VisibilityTimeout)

        Returns:
        -------
            Queue URL

        """
        ...

    def delete_queue(self, queue_url: str) -> None:
        """
        Delete a queue.

        Args:
        ----
            queue_url: URL of the queue to delete

        """
        ...

    def send_message(
        self,
        queue_url: str,
        message_body: str,
        message_attributes: dict[str, Any] | None = None,
    ) -> str:
        """
        Send a message to the queue.

        Args:
        ----
            queue_url: URL of the queue
            message_body: Message content
            message_attributes: Optional message attributes

        Returns:
        -------
            Message ID

        """
        ...

    def receive_messages(
        self,
        queue_url: str,
        max_messages: int = 1,
        wait_time_seconds: int = 0,
    ) -> list[dict[str, Any]]:
        """
        Receive messages from the queue.

        Args:
        ----
            queue_url: URL of the queue
            max_messages: Maximum number of messages to receive (1-10)
            wait_time_seconds: Long polling wait time

        Returns:
        -------
            List of message dictionaries

        """
        ...

    def delete_message(self, queue_url: str, receipt_handle: str) -> None:
        """
        Delete a message from the queue.

        Args:
        ----
            queue_url: URL of the queue
            receipt_handle: Receipt handle from received message

        """
        ...


@runtime_checkable
class SecretManagerProtocol(Protocol):
    """
    Protocol for secrets management operations.

    This protocol defines the interface for secrets management that works across
    all providers (AWS Secrets Manager, LocalStack, etc.).
    """

    def create_secret(self, name: str, secret_value: str, description: str | None = None) -> str:
        """
        Create a new secret.

        Args:
        ----
            name: Secret name
            secret_value: Secret value (string or JSON)
            description: Optional description

        Returns:
        -------
            Secret ARN

        """
        ...

    def get_secret_value(self, name: str) -> str:
        """
        Get the value of a secret.

        Args:
        ----
            name: Secret name

        Returns:
        -------
            Secret value

        """
        ...

    def update_secret(self, name: str, secret_value: str) -> None:
        """
        Update a secret's value.

        Args:
        ----
            name: Secret name
            secret_value: New secret value

        """
        ...

    def delete_secret(self, name: str, force_delete: bool = False) -> None:
        """
        Delete a secret.

        Args:
        ----
            name: Secret name
            force_delete: If True, delete immediately without recovery window

        """
        ...


@runtime_checkable
class CloudProviderProtocol(Protocol):
    """
    Protocol for cloud provider factory.

    This protocol defines the factory interface for creating cloud service clients.
    Each provider implementation (AWS, LocalStack, GCP, etc.) provides a factory
    that creates appropriately configured service clients.
    """

    def create_object_storage(self) -> ObjectStorageProtocol:
        """
        Create an object storage client.

        Returns
        -------
            Object storage client implementing ObjectStorageProtocol

        """
        ...

    def create_queue(self) -> QueueProtocol:
        """
        Create a message queue client.

        Returns
        -------
            Queue client implementing QueueProtocol

        """
        ...

    def create_secret_manager(self) -> SecretManagerProtocol:
        """
        Create a secrets manager client.

        Returns
        -------
            Secrets manager client implementing SecretManagerProtocol

        """
        ...

    def close(self) -> None:
        """
        Close all client connections and cleanup resources.

        This should be called when the provider is no longer needed.
        """
        ...

    def __enter__(self) -> "CloudProviderProtocol":
        """Context manager entry."""
        ...

    def __exit__(self, exc_type: Any, exc_val: Any, exc_tb: Any) -> None:
        """Context manager exit with cleanup."""
        ...

    async def __aenter__(self) -> "CloudProviderProtocol":
        """Async context manager entry."""
        ...

    async def __aexit__(self, exc_type: Any, exc_val: Any, exc_tb: Any) -> None:
        """Async context manager exit with cleanup."""
        ...
