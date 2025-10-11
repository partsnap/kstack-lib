"""Tests for CAL protocol definitions."""

from pathlib import Path
from typing import Any, BinaryIO

import pytest

from kstack_lib.cal.protocols import (
    CloudProviderProtocol,
    ObjectStorageProtocol,
    QueueProtocol,
    SecretManagerProtocol,
)


class MockObjectStorage:
    """Mock implementation of ObjectStorageProtocol for testing."""

    def list_buckets(self) -> list[str]:
        return ["bucket1", "bucket2"]

    def create_bucket(self, bucket_name: str) -> None:
        pass

    def delete_bucket(self, bucket_name: str) -> None:
        pass

    def list_objects(self, bucket_name: str, prefix: str = "") -> list[dict[str, Any]]:
        return [{"Key": "test.txt", "Size": 100}]

    def upload_object(
        self,
        bucket_name: str,
        object_key: str,
        file_path: Path | None = None,
        file_obj: BinaryIO | None = None,
        content_type: str | None = None,
        metadata: dict[str, str] | None = None,
    ) -> None:
        pass

    def download_object(
        self,
        bucket_name: str,
        object_key: str,
        file_path: Path | None = None,
    ) -> bytes | None:
        if file_path:
            return None
        return b"test data"

    def delete_object(self, bucket_name: str, object_key: str) -> None:
        pass

    def generate_presigned_url(
        self,
        bucket_name: str,
        object_key: str,
        expiration: int = 3600,
        http_method: str = "GET",
    ) -> str:
        return f"https://example.com/{bucket_name}/{object_key}"

    def get_object_metadata(self, bucket_name: str, object_key: str) -> dict[str, Any]:
        return {
            "ContentLength": 100,
            "ContentType": "text/plain",
            "ETag": "abc123",
        }


class MockQueue:
    """Mock implementation of QueueProtocol for testing."""

    def create_queue(self, queue_name: str, attributes: dict[str, str] | None = None) -> str:
        return f"https://sqs.example.com/queue/{queue_name}"

    def delete_queue(self, queue_url: str) -> None:
        pass

    def send_message(
        self,
        queue_url: str,
        message_body: str,
        message_attributes: dict[str, Any] | None = None,
    ) -> str:
        return "msg-123"

    def receive_messages(
        self,
        queue_url: str,
        max_messages: int = 1,
        wait_time_seconds: int = 0,
    ) -> list[dict[str, Any]]:
        return [{"MessageId": "msg-123", "Body": "test"}]

    def delete_message(self, queue_url: str, receipt_handle: str) -> None:
        pass


class MockSecretManager:
    """Mock implementation of SecretManagerProtocol for testing."""

    def create_secret(self, name: str, secret_value: str, description: str | None = None) -> str:
        return f"arn:aws:secretsmanager:us-west-2:123:secret:{name}"

    def get_secret_value(self, name: str) -> str:
        return "secret-value"

    def update_secret(self, name: str, secret_value: str) -> None:
        pass

    def delete_secret(self, name: str, force_delete: bool = False) -> None:
        pass


class MockCloudProvider:
    """Mock implementation of CloudProviderProtocol for testing."""

    def create_object_storage(self) -> ObjectStorageProtocol:
        return MockObjectStorage()

    def create_queue(self) -> QueueProtocol:
        return MockQueue()

    def create_secret_manager(self) -> SecretManagerProtocol:
        return MockSecretManager()

    def close(self) -> None:
        pass

    def __enter__(self) -> "MockCloudProvider":
        return self

    def __exit__(self, exc_type: Any, exc_val: Any, exc_tb: Any) -> None:
        self.close()

    async def __aenter__(self) -> "MockCloudProvider":
        return self

    async def __aexit__(self, exc_type: Any, exc_val: Any, exc_tb: Any) -> None:
        self.close()


class TestProtocolConformance:
    """Tests that mock implementations conform to protocols."""

    def test_object_storage_protocol_conformance(self):
        """Test that MockObjectStorage conforms to ObjectStorageProtocol."""
        storage = MockObjectStorage()
        assert isinstance(storage, ObjectStorageProtocol)

    def test_queue_protocol_conformance(self):
        """Test that MockQueue conforms to QueueProtocol."""
        queue = MockQueue()
        assert isinstance(queue, QueueProtocol)

    def test_secret_manager_protocol_conformance(self):
        """Test that MockSecretManager conforms to SecretManagerProtocol."""
        secrets = MockSecretManager()
        assert isinstance(secrets, SecretManagerProtocol)

    def test_cloud_provider_protocol_conformance(self):
        """Test that MockCloudProvider conforms to CloudProviderProtocol."""
        provider = MockCloudProvider()
        assert isinstance(provider, CloudProviderProtocol)


class TestProtocolMethods:
    """Tests that protocol methods work as expected."""

    def test_object_storage_methods(self):
        """Test ObjectStorageProtocol methods."""
        storage = MockObjectStorage()

        # Test list_buckets
        buckets = storage.list_buckets()
        assert isinstance(buckets, list)
        assert len(buckets) == 2

        # Test list_objects
        objects = storage.list_objects("bucket1")
        assert isinstance(objects, list)
        assert len(objects) == 1

        # Test download_object
        data = storage.download_object("bucket1", "test.txt")
        assert data == b"test data"

        # Test generate_presigned_url
        url = storage.generate_presigned_url("bucket1", "test.txt")
        assert "bucket1" in url
        assert "test.txt" in url

        # Test get_object_metadata
        metadata = storage.get_object_metadata("bucket1", "test.txt")
        assert metadata["ContentLength"] == 100

    def test_queue_methods(self):
        """Test QueueProtocol methods."""
        queue = MockQueue()

        # Test create_queue
        queue_url = queue.create_queue("test-queue")
        assert "test-queue" in queue_url

        # Test send_message
        msg_id = queue.send_message(queue_url, "test message")
        assert msg_id == "msg-123"

        # Test receive_messages
        messages = queue.receive_messages(queue_url)
        assert isinstance(messages, list)
        assert len(messages) == 1

    def test_secret_manager_methods(self):
        """Test SecretManagerProtocol methods."""
        secrets = MockSecretManager()

        # Test create_secret
        arn = secrets.create_secret("my-secret", "value")
        assert "my-secret" in arn

        # Test get_secret_value
        value = secrets.get_secret_value("my-secret")
        assert value == "secret-value"

    def test_cloud_provider_factory_methods(self):
        """Test CloudProviderProtocol factory methods."""
        provider = MockCloudProvider()

        # Test create_object_storage
        storage = provider.create_object_storage()
        assert isinstance(storage, ObjectStorageProtocol)

        # Test create_queue
        queue = provider.create_queue()
        assert isinstance(queue, QueueProtocol)

        # Test create_secret_manager
        secrets = provider.create_secret_manager()
        assert isinstance(secrets, SecretManagerProtocol)

    def test_cloud_provider_context_manager(self):
        """Test CloudProviderProtocol context manager."""
        with MockCloudProvider() as provider:
            assert isinstance(provider, CloudProviderProtocol)
            storage = provider.create_object_storage()
            assert isinstance(storage, ObjectStorageProtocol)

    @pytest.mark.asyncio
    async def test_cloud_provider_async_context_manager(self):
        """Test CloudProviderProtocol async context manager."""
        async with MockCloudProvider() as provider:
            assert isinstance(provider, CloudProviderProtocol)
            storage = provider.create_object_storage()
            assert isinstance(storage, ObjectStorageProtocol)
