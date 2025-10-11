"""Tests for AWS family adapter implementations."""

from datetime import datetime
from unittest.mock import MagicMock, patch

import pytest

from kstack_lib.cal.adapters.aws_family import (
    AWSFamilyProvider,
    AWSObjectStorage,
    AWSQueue,
    AWSSecretManager,
)
from kstack_lib.cal.protocols import (
    ObjectStorageProtocol,
    QueueProtocol,
    SecretManagerProtocol,
)
from kstack_lib.config.schemas import ProviderConfig


@pytest.fixture
def mock_s3_client():
    """Create a mock S3 client."""
    client = MagicMock()
    client.meta.region_name = "us-west-2"
    return client


@pytest.fixture
def mock_sqs_client():
    """Create a mock SQS client."""
    return MagicMock()


@pytest.fixture
def mock_secrets_client():
    """Create a mock Secrets Manager client."""
    return MagicMock()


class TestAWSObjectStorage:
    """Tests for AWSObjectStorage adapter."""

    def test_list_buckets(self, mock_s3_client):
        """Test listing buckets."""
        mock_s3_client.list_buckets.return_value = {"Buckets": [{"Name": "bucket1"}, {"Name": "bucket2"}]}

        storage = AWSObjectStorage(mock_s3_client)
        buckets = storage.list_buckets()

        assert len(buckets) == 2
        assert "bucket1" in buckets
        assert "bucket2" in buckets
        mock_s3_client.list_buckets.assert_called_once()

    def test_create_bucket_us_east_1(self, mock_s3_client):
        """Test creating bucket in us-east-1 (no LocationConstraint)."""
        mock_s3_client.meta.region_name = "us-east-1"

        storage = AWSObjectStorage(mock_s3_client)
        storage.create_bucket("test-bucket")

        mock_s3_client.create_bucket.assert_called_once_with(Bucket="test-bucket")

    def test_create_bucket_other_region(self, mock_s3_client):
        """Test creating bucket in non-us-east-1 region."""
        mock_s3_client.meta.region_name = "us-west-2"

        storage = AWSObjectStorage(mock_s3_client)
        storage.create_bucket("test-bucket")

        mock_s3_client.create_bucket.assert_called_once_with(
            Bucket="test-bucket",
            CreateBucketConfiguration={"LocationConstraint": "us-west-2"},
        )

    def test_delete_bucket(self, mock_s3_client):
        """Test deleting bucket."""
        storage = AWSObjectStorage(mock_s3_client)
        storage.delete_bucket("test-bucket")

        mock_s3_client.delete_bucket.assert_called_once_with(Bucket="test-bucket")

    def test_list_objects(self, mock_s3_client):
        """Test listing objects."""
        mock_s3_client.list_objects_v2.return_value = {
            "Contents": [
                {"Key": "file1.txt", "Size": 100},
                {"Key": "file2.txt", "Size": 200},
            ]
        }

        storage = AWSObjectStorage(mock_s3_client)
        objects = storage.list_objects("test-bucket", prefix="files/")

        assert len(objects) == 2
        assert objects[0]["Key"] == "file1.txt"
        mock_s3_client.list_objects_v2.assert_called_once_with(Bucket="test-bucket", Prefix="files/")

    def test_upload_object_from_file(self, mock_s3_client, tmp_path):
        """Test uploading object from file path."""
        test_file = tmp_path / "test.txt"
        test_file.write_text("test content")

        storage = AWSObjectStorage(mock_s3_client)
        storage.upload_object("test-bucket", "test.txt", file_path=test_file)

        mock_s3_client.upload_file.assert_called_once()
        args = mock_s3_client.upload_file.call_args
        assert args[0][0] == str(test_file)
        assert args[0][1] == "test-bucket"
        assert args[0][2] == "test.txt"

    def test_upload_object_with_content_type(self, mock_s3_client, tmp_path):
        """Test uploading object with explicit content type."""
        test_file = tmp_path / "test.json"
        test_file.write_text('{"key": "value"}')

        storage = AWSObjectStorage(mock_s3_client)
        storage.upload_object(
            "test-bucket",
            "test.json",
            file_path=test_file,
            content_type="application/json",
        )

        args = mock_s3_client.upload_file.call_args
        assert args[1]["ExtraArgs"]["ContentType"] == "application/json"

    def test_download_object_to_bytes(self, mock_s3_client):
        """Test downloading object to bytes."""
        mock_response = {"Body": MagicMock()}
        mock_response["Body"].read.return_value = b"test content"
        mock_s3_client.get_object.return_value = mock_response

        storage = AWSObjectStorage(mock_s3_client)
        data = storage.download_object("test-bucket", "test.txt")

        assert data == b"test content"
        mock_s3_client.get_object.assert_called_once_with(Bucket="test-bucket", Key="test.txt")

    def test_delete_object(self, mock_s3_client):
        """Test deleting object."""
        storage = AWSObjectStorage(mock_s3_client)
        storage.delete_object("test-bucket", "test.txt")

        mock_s3_client.delete_object.assert_called_once_with(Bucket="test-bucket", Key="test.txt")

    def test_generate_presigned_url(self, mock_s3_client):
        """Test generating presigned URL."""
        mock_s3_client.generate_presigned_url.return_value = "https://s3.amazonaws.com/bucket/key?signature=abc"

        storage = AWSObjectStorage(mock_s3_client)
        url = storage.generate_presigned_url("test-bucket", "test.txt", expiration=3600)

        assert "signature" in url
        mock_s3_client.generate_presigned_url.assert_called_once()

    def test_generate_presigned_url_with_custom_domain(self, mock_s3_client):
        """Test generating presigned URL with custom domain (LocalStack)."""
        mock_s3_client.generate_presigned_url.return_value = "http://localstack:4566/bucket/key?signature=abc"

        storage = AWSObjectStorage(mock_s3_client, presigned_url_domain="localstack.dev.partsnap.local")
        url = storage.generate_presigned_url("test-bucket", "test.txt")

        assert "localstack.dev.partsnap.local" in url

    def test_get_object_metadata(self, mock_s3_client):
        """Test getting object metadata."""
        mock_s3_client.head_object.return_value = {
            "ContentLength": 1024,
            "ContentType": "text/plain",
            "LastModified": datetime(2025, 1, 10),
            "Metadata": {"custom": "value"},
            "ETag": '"abc123"',
        }

        storage = AWSObjectStorage(mock_s3_client)
        metadata = storage.get_object_metadata("test-bucket", "test.txt")

        assert metadata["ContentLength"] == 1024
        assert metadata["ContentType"] == "text/plain"
        assert metadata["Metadata"]["custom"] == "value"


class TestAWSQueue:
    """Tests for AWSQueue adapter."""

    def test_create_queue(self, mock_sqs_client):
        """Test creating queue."""
        mock_sqs_client.create_queue.return_value = {"QueueUrl": "https://sqs.us-west-2.amazonaws.com/123/test-queue"}

        queue = AWSQueue(mock_sqs_client)
        queue_url = queue.create_queue("test-queue")

        assert "test-queue" in queue_url
        mock_sqs_client.create_queue.assert_called_once_with(QueueName="test-queue")

    def test_create_queue_with_attributes(self, mock_sqs_client):
        """Test creating queue with attributes."""
        mock_sqs_client.create_queue.return_value = {"QueueUrl": "https://sqs.us-west-2.amazonaws.com/123/test-queue"}

        queue = AWSQueue(mock_sqs_client)
        queue.create_queue("test-queue", attributes={"VisibilityTimeout": "60"})

        args = mock_sqs_client.create_queue.call_args
        assert args[1]["Attributes"]["VisibilityTimeout"] == "60"

    def test_delete_queue(self, mock_sqs_client):
        """Test deleting queue."""
        queue = AWSQueue(mock_sqs_client)
        queue.delete_queue("https://sqs.us-west-2.amazonaws.com/123/test-queue")

        mock_sqs_client.delete_queue.assert_called_once()

    def test_send_message(self, mock_sqs_client):
        """Test sending message."""
        mock_sqs_client.send_message.return_value = {"MessageId": "msg-123"}

        queue = AWSQueue(mock_sqs_client)
        msg_id = queue.send_message("queue-url", "test message")

        assert msg_id == "msg-123"
        mock_sqs_client.send_message.assert_called_once()

    def test_receive_messages(self, mock_sqs_client):
        """Test receiving messages."""
        mock_sqs_client.receive_message.return_value = {"Messages": [{"MessageId": "msg-123", "Body": "test"}]}

        queue = AWSQueue(mock_sqs_client)
        messages = queue.receive_messages("queue-url", max_messages=10, wait_time_seconds=5)

        assert len(messages) == 1
        assert messages[0]["MessageId"] == "msg-123"
        mock_sqs_client.receive_message.assert_called_once_with(
            QueueUrl="queue-url", MaxNumberOfMessages=10, WaitTimeSeconds=5
        )

    def test_delete_message(self, mock_sqs_client):
        """Test deleting message."""
        queue = AWSQueue(mock_sqs_client)
        queue.delete_message("queue-url", "receipt-handle-123")

        mock_sqs_client.delete_message.assert_called_once_with(QueueUrl="queue-url", ReceiptHandle="receipt-handle-123")


class TestAWSSecretManager:
    """Tests for AWSSecretManager adapter."""

    def test_create_secret(self, mock_secrets_client):
        """Test creating secret."""
        mock_secrets_client.create_secret.return_value = {"ARN": "arn:aws:secretsmanager:us-west-2:123:secret:test"}

        secrets = AWSSecretManager(mock_secrets_client)
        arn = secrets.create_secret("test-secret", "secret-value")

        assert "test" in arn
        mock_secrets_client.create_secret.assert_called_once()

    def test_get_secret_value(self, mock_secrets_client):
        """Test getting secret value."""
        mock_secrets_client.get_secret_value.return_value = {"SecretString": "my-secret"}

        secrets = AWSSecretManager(mock_secrets_client)
        value = secrets.get_secret_value("test-secret")

        assert value == "my-secret"
        mock_secrets_client.get_secret_value.assert_called_once_with(SecretId="test-secret")

    def test_update_secret(self, mock_secrets_client):
        """Test updating secret."""
        secrets = AWSSecretManager(mock_secrets_client)
        secrets.update_secret("test-secret", "new-value")

        mock_secrets_client.update_secret.assert_called_once_with(SecretId="test-secret", SecretString="new-value")

    def test_delete_secret(self, mock_secrets_client):
        """Test deleting secret."""
        secrets = AWSSecretManager(mock_secrets_client)
        secrets.delete_secret("test-secret")

        mock_secrets_client.delete_secret.assert_called_once_with(SecretId="test-secret")

    def test_delete_secret_force(self, mock_secrets_client):
        """Test force deleting secret."""
        secrets = AWSSecretManager(mock_secrets_client)
        secrets.delete_secret("test-secret", force_delete=True)

        args = mock_secrets_client.delete_secret.call_args
        assert args[1]["ForceDeleteWithoutRecovery"] is True


class TestAWSFamilyProvider:
    """Tests for AWSFamilyProvider."""

    def test_protocol_conformance(self):
        """Test that provider conforms to CloudProviderProtocol."""
        from kstack_lib.cal.protocols import CloudProviderProtocol

        config = MagicMock(spec=ProviderConfig)
        config.services = {}
        config.region = "us-west-2"
        config.verify_ssl = True

        credentials = {"aws_access_key_id": "test", "aws_secret_access_key": "test"}

        provider = AWSFamilyProvider(config, credentials)
        assert isinstance(provider, CloudProviderProtocol)

    @patch("kstack_lib.cal.adapters.aws_family.boto3.client")
    def test_create_object_storage(self, mock_boto_client):
        """Test creating object storage client."""
        mock_client = MagicMock()
        mock_boto_client.return_value = mock_client

        config = MagicMock(spec=ProviderConfig)
        config.services = {"s3": MagicMock()}
        config.services["s3"].endpoint_url = None
        config.services["s3"].presigned_url_domain = None
        config.region = "us-west-2"
        config.verify_ssl = True

        credentials = {"aws_access_key_id": "test", "aws_secret_access_key": "test"}

        provider = AWSFamilyProvider(config, credentials)
        storage = provider.create_object_storage()

        assert isinstance(storage, ObjectStorageProtocol)
        mock_boto_client.assert_called_once()

    @patch("kstack_lib.cal.adapters.aws_family.boto3.client")
    def test_create_queue(self, mock_boto_client):
        """Test creating queue client."""
        mock_client = MagicMock()
        mock_boto_client.return_value = mock_client

        config = MagicMock(spec=ProviderConfig)
        config.services = {}
        config.region = "us-west-2"
        config.verify_ssl = True

        credentials = {"aws_access_key_id": "test", "aws_secret_access_key": "test"}

        provider = AWSFamilyProvider(config, credentials)
        queue = provider.create_queue()

        assert isinstance(queue, QueueProtocol)

    @patch("kstack_lib.cal.adapters.aws_family.boto3.client")
    def test_create_secret_manager(self, mock_boto_client):
        """Test creating secret manager client."""
        mock_client = MagicMock()
        mock_boto_client.return_value = mock_client

        config = MagicMock(spec=ProviderConfig)
        config.services = {}
        config.region = "us-west-2"
        config.verify_ssl = True

        credentials = {"aws_access_key_id": "test", "aws_secret_access_key": "test"}

        provider = AWSFamilyProvider(config, credentials)
        secrets = provider.create_secret_manager()

        assert isinstance(secrets, SecretManagerProtocol)

    @patch("kstack_lib.cal.adapters.aws_family.boto3.client")
    def test_context_manager(self, mock_boto_client):
        """Test context manager usage."""
        mock_client = MagicMock()
        mock_boto_client.return_value = mock_client

        config = MagicMock(spec=ProviderConfig)
        config.services = {"s3": MagicMock()}
        config.services["s3"].endpoint_url = None
        config.services["s3"].presigned_url_domain = None
        config.region = "us-west-2"
        config.verify_ssl = True

        credentials = {"aws_access_key_id": "test", "aws_secret_access_key": "test"}

        with AWSFamilyProvider(config, credentials) as provider:
            assert isinstance(provider, AWSFamilyProvider)
            # Create a service to actually instantiate a client
            provider.create_object_storage()

        # Client should be closed
        mock_client.close.assert_called()
