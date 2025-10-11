"""
AWS Family Cloud Adapter.

This module provides implementations of cloud service protocols for the AWS family:
- AWS (production AWS services)
- LocalStack (local development)
- DigitalOcean Spaces (S3-compatible object storage)
- MinIO (self-hosted S3-compatible storage)

All implementations use boto3/aioboto3 clients configured with appropriate endpoints
and credentials.
"""

import mimetypes
from pathlib import Path
from typing import Any, BinaryIO

import boto3
from botocore.client import Config
from botocore.exceptions import ClientError

from kstack_lib.cal.protocols import (
    ObjectStorageProtocol,
    QueueProtocol,
    SecretManagerProtocol,
)
from kstack_lib.config.schemas import ProviderConfig


class AWSObjectStorage:
    """
    AWS S3-compatible object storage implementation.

    Works with AWS S3, LocalStack, DigitalOcean Spaces, MinIO, and any other
    S3-compatible storage provider.
    """

    def __init__(
        self,
        client: Any,
        presigned_url_domain: str | None = None,
    ):
        """
        Initialize AWS object storage adapter.

        Args:
        ----
            client: boto3 S3 client
            presigned_url_domain: Optional custom domain for presigned URLs
                                 (used by LocalStack and DigitalOcean Spaces)

        """
        self._client = client
        self._presigned_url_domain = presigned_url_domain

    def list_buckets(self) -> list[str]:
        """List all buckets."""
        response = self._client.list_buckets()
        return [bucket["Name"] for bucket in response.get("Buckets", [])]

    def create_bucket(self, bucket_name: str) -> None:
        """Create a new bucket."""
        try:
            # For us-east-1, don't specify LocationConstraint
            region = self._client.meta.region_name
            if region == "us-east-1":
                self._client.create_bucket(Bucket=bucket_name)
            else:
                self._client.create_bucket(
                    Bucket=bucket_name,
                    CreateBucketConfiguration={"LocationConstraint": region},
                )
        except ClientError as e:
            if e.response["Error"]["Code"] != "BucketAlreadyOwnedByYou":
                raise

    def delete_bucket(self, bucket_name: str) -> None:
        """Delete a bucket (must be empty)."""
        self._client.delete_bucket(Bucket=bucket_name)

    def list_objects(self, bucket_name: str, prefix: str = "") -> list[dict[str, Any]]:
        """List objects in a bucket with optional prefix filtering."""
        try:
            response = self._client.list_objects_v2(Bucket=bucket_name, Prefix=prefix)
            return response.get("Contents", [])
        except ClientError:
            return []

    def upload_object(
        self,
        bucket_name: str,
        object_key: str,
        file_path: Path | None = None,
        file_obj: BinaryIO | None = None,
        content_type: str | None = None,
        metadata: dict[str, str] | None = None,
    ) -> None:
        """Upload an object to the bucket."""
        if file_path is None and file_obj is None:
            raise ValueError("Either file_path or file_obj must be provided")
        if file_path is not None and file_obj is not None:
            raise ValueError("Only one of file_path or file_obj should be provided")

        # Auto-detect content type if not provided
        if content_type is None and file_path is not None:
            content_type, _ = mimetypes.guess_type(str(file_path))

        extra_args: dict[str, Any] = {}
        if content_type:
            extra_args["ContentType"] = content_type
        if metadata:
            extra_args["Metadata"] = metadata

        if file_path is not None:
            self._client.upload_file(str(file_path), bucket_name, object_key, ExtraArgs=extra_args)
        else:
            self._client.upload_fileobj(file_obj, bucket_name, object_key, ExtraArgs=extra_args)

    def download_object(
        self,
        bucket_name: str,
        object_key: str,
        file_path: Path | None = None,
    ) -> bytes | None:
        """Download an object from the bucket."""
        if file_path is not None:
            self._client.download_file(bucket_name, object_key, str(file_path))
            return None
        else:
            response = self._client.get_object(Bucket=bucket_name, Key=object_key)
            return response["Body"].read()

    def delete_object(self, bucket_name: str, object_key: str) -> None:
        """Delete an object from the bucket."""
        self._client.delete_object(Bucket=bucket_name, Key=object_key)

    def generate_presigned_url(
        self,
        bucket_name: str,
        object_key: str,
        expiration: int = 3600,
        http_method: str = "GET",
    ) -> str:
        """Generate a presigned URL for temporary access to an object."""
        method_map = {
            "GET": "get_object",
            "PUT": "put_object",
            "DELETE": "delete_object",
        }

        client_method = method_map.get(http_method.upper())
        if client_method is None:
            raise ValueError(f"Unsupported HTTP method: {http_method}")

        url = self._client.generate_presigned_url(
            ClientMethod=client_method,
            Params={"Bucket": bucket_name, "Key": object_key},
            ExpiresIn=expiration,
        )

        # Replace endpoint with custom domain if specified (for LocalStack/DO Spaces)
        if self._presigned_url_domain:
            # Extract the path and query from the URL
            from urllib.parse import urlparse, urlunparse

            parsed = urlparse(url)
            # Rebuild URL with custom domain
            url = urlunparse(
                (
                    parsed.scheme,
                    self._presigned_url_domain,
                    parsed.path,
                    parsed.params,
                    parsed.query,
                    parsed.fragment,
                )
            )

        return url

    def get_object_metadata(self, bucket_name: str, object_key: str) -> dict[str, Any]:
        """Get metadata for an object."""
        response = self._client.head_object(Bucket=bucket_name, Key=object_key)
        return {
            "ContentLength": response["ContentLength"],
            "ContentType": response.get("ContentType"),
            "LastModified": response["LastModified"],
            "Metadata": response.get("Metadata", {}),
            "ETag": response["ETag"],
        }


class AWSQueue:
    """AWS SQS-compatible message queue implementation."""

    def __init__(self, client: Any):
        """
        Initialize AWS queue adapter.

        Args:
        ----
            client: boto3 SQS client

        """
        self._client = client

    def create_queue(self, queue_name: str, attributes: dict[str, str] | None = None) -> str:
        """Create a new queue."""
        kwargs: dict[str, Any] = {"QueueName": queue_name}
        if attributes:
            kwargs["Attributes"] = attributes

        response = self._client.create_queue(**kwargs)
        return response["QueueUrl"]

    def delete_queue(self, queue_url: str) -> None:
        """Delete a queue."""
        self._client.delete_queue(QueueUrl=queue_url)

    def send_message(
        self,
        queue_url: str,
        message_body: str,
        message_attributes: dict[str, Any] | None = None,
    ) -> str:
        """Send a message to the queue."""
        kwargs: dict[str, Any] = {
            "QueueUrl": queue_url,
            "MessageBody": message_body,
        }
        if message_attributes:
            kwargs["MessageAttributes"] = message_attributes

        response = self._client.send_message(**kwargs)
        return response["MessageId"]

    def receive_messages(
        self,
        queue_url: str,
        max_messages: int = 1,
        wait_time_seconds: int = 0,
    ) -> list[dict[str, Any]]:
        """Receive messages from the queue."""
        response = self._client.receive_message(
            QueueUrl=queue_url,
            MaxNumberOfMessages=max_messages,
            WaitTimeSeconds=wait_time_seconds,
        )
        return response.get("Messages", [])

    def delete_message(self, queue_url: str, receipt_handle: str) -> None:
        """Delete a message from the queue."""
        self._client.delete_message(QueueUrl=queue_url, ReceiptHandle=receipt_handle)


class AWSSecretManager:
    """AWS Secrets Manager implementation."""

    def __init__(self, client: Any):
        """
        Initialize AWS secret manager adapter.

        Args:
        ----
            client: boto3 Secrets Manager client

        """
        self._client = client

    def create_secret(self, name: str, secret_value: str, description: str | None = None) -> str:
        """Create a new secret."""
        kwargs: dict[str, Any] = {
            "Name": name,
            "SecretString": secret_value,
        }
        if description:
            kwargs["Description"] = description

        response = self._client.create_secret(**kwargs)
        return response["ARN"]

    def get_secret_value(self, name: str) -> str:
        """Get the value of a secret."""
        response = self._client.get_secret_value(SecretId=name)
        return response["SecretString"]

    def update_secret(self, name: str, secret_value: str) -> None:
        """Update a secret's value."""
        self._client.update_secret(SecretId=name, SecretString=secret_value)

    def delete_secret(self, name: str, force_delete: bool = False) -> None:
        """Delete a secret."""
        kwargs: dict[str, Any] = {"SecretId": name}
        if force_delete:
            kwargs["ForceDeleteWithoutRecovery"] = True

        self._client.delete_secret(**kwargs)


class AWSFamilyProvider:
    """
    Cloud provider for AWS family (AWS, LocalStack, DigitalOcean, MinIO).

    This provider creates boto3 clients configured for different AWS-compatible
    services based on the provider configuration.
    """

    def __init__(
        self,
        config: ProviderConfig,
        credentials: dict[str, str],
    ):
        """
        Initialize AWS family provider.

        Args:
        ----
            config: Provider configuration with endpoints and settings
            credentials: AWS credentials (aws_access_key_id, aws_secret_access_key)

        """
        self._config = config
        self._credentials = credentials
        self._clients: dict[str, Any] = {}

    def _create_boto3_client(self, service: str) -> Any:
        """
        Create a boto3 client for the specified service.

        Args:
        ----
            service: Service name (s3, sqs, secretsmanager)

        Returns:
        -------
            Configured boto3 client

        """
        # Get service-specific configuration
        service_config: Any = self._config.services.get(service, {})

        # Build client configuration
        client_config = Config(
            signature_version="s3v4" if service == "s3" else None,
            s3={"addressing_style": "path"} if service == "s3" else None,
        )

        kwargs: dict[str, Any] = {
            "service_name": service,
            "aws_access_key_id": self._credentials["aws_access_key_id"],
            "aws_secret_access_key": self._credentials["aws_secret_access_key"],
            "region_name": self._config.region,
            "config": client_config,
        }

        # Add endpoint URL if specified (for LocalStack, DigitalOcean, MinIO)
        if hasattr(service_config, "endpoint_url") and service_config.endpoint_url:
            kwargs["endpoint_url"] = service_config.endpoint_url

        # Add SSL verification setting
        if not self._config.verify_ssl:
            kwargs["verify"] = False

        return boto3.client(**kwargs)

    def create_object_storage(self) -> ObjectStorageProtocol:
        """Create an object storage client."""
        if "s3" not in self._clients:
            self._clients["s3"] = self._create_boto3_client("s3")

        # Get presigned URL domain from config
        service_config = self._config.services.get("s3")
        presigned_url_domain = None
        if service_config and hasattr(service_config, "presigned_url_domain"):
            presigned_url_domain = service_config.presigned_url_domain

        return AWSObjectStorage(
            client=self._clients["s3"],
            presigned_url_domain=presigned_url_domain,
        )

    def create_queue(self) -> QueueProtocol:
        """Create a message queue client."""
        if "sqs" not in self._clients:
            self._clients["sqs"] = self._create_boto3_client("sqs")

        return AWSQueue(client=self._clients["sqs"])

    def create_secret_manager(self) -> SecretManagerProtocol:
        """Create a secrets manager client."""
        if "secretsmanager" not in self._clients:
            self._clients["secretsmanager"] = self._create_boto3_client("secretsmanager")

        return AWSSecretManager(client=self._clients["secretsmanager"])

    def close(self) -> None:
        """Close all client connections and cleanup resources."""
        for client in self._clients.values():
            if hasattr(client, "close"):
                client.close()
        self._clients.clear()

    def __enter__(self) -> "AWSFamilyProvider":
        """Context manager entry."""
        return self

    def __exit__(self, exc_type: Any, exc_val: Any, exc_tb: Any) -> None:
        """Context manager exit with cleanup."""
        self.close()

    async def __aenter__(self) -> "AWSFamilyProvider":
        """Async context manager entry."""
        return self

    async def __aexit__(self, exc_type: Any, exc_val: Any, exc_tb: Any) -> None:
        """Async context manager exit with cleanup."""
        self.close()
