# Testing Guide

This guide covers how to test kstack-lib and services that depend on it.

## Running Tests

### Full Test Suite

```bash
make test
```

This runs all tests except cluster-specific tests (which require a real Kubernetes environment).

### With Coverage

```bash
make test-cov
```

Generates coverage report showing which code is tested.

### Specific Test Files

```bash
# Run a specific test file
uv run pytest tests/test_configmap.py -v

# Run a specific test
uv run pytest tests/test_configmap.py::test_load_config -v

# Run tests matching a pattern
uv run pytest -k "config" -v
```

## Test Organization

```
tests/
├── any/              # Tests for shared code (future)
├── cal/              # Cloud Abstraction Layer tests
├── cluster/          # Cluster adapter tests (skipped locally)
├── config/           # Configuration loading tests
├── integration/      # Integration tests (require services)
├── test_configmap.py
├── test_container.py  # IoC container tests
├── test_exceptions.py
├── test_local_environment.py
└── test_types.py
```

## Testing Strategy

### Unit Tests

Test individual modules in isolation with mocks:

```python
from unittest.mock import MagicMock, patch
import pytest
from kstack_lib.local.config.environment import LocalEnvironmentDetector

def test_environment_detection():
    """Test local environment detector."""
    detector = LocalEnvironmentDetector(config_root="/path/to/config")
    env = detector.get_environment()
    assert env in ["development", "staging", "production"]
```

### Integration Tests

Test with real services (LocalStack, Redis):

```python
@pytest.mark.integration
def test_s3_upload():
    """Test S3 upload with real LocalStack."""
    from kstack_lib import get_cloud_storage_adapter

    storage = get_cloud_storage_adapter(service="s3")

    # Upload test file
    storage.upload_file(
        bucket="test-bucket",
        key="test.txt",
        body=b"test data"
    )

    # Verify upload
    response = storage.download_file(bucket="test-bucket", key="test.txt")
    assert response["Body"].read() == b"test data"
```

Run integration tests:

```bash
# Requires LocalStack and Redis running
uv run pytest tests/integration/ -v
```

### Cluster Tests

Cluster tests use mockable base class guards to enable testing outside Kubernetes:

```python
# tests/cluster/test_secrets.py
from unittest.mock import patch
from kstack_lib.cluster._base import ClusterBase

class TestClusterSecretsProvider:
    """Test ClusterSecretsProvider with mocked dependencies."""

    @patch.object(ClusterBase, "_check_cluster_context")
    @patch("kstack_lib.cluster.security.secrets.run_command")
    def test_get_credentials_success(self, mock_run, mock_guard):
        """Test successful credential retrieval."""
        from kstack_lib.cluster.security.secrets import ClusterSecretsProvider

        # Mock kubectl output
        secret_data = {"data": {"key": base64.b64encode(b"value").decode()}}
        mock_run.return_value = MagicMock(stdout=json.dumps(secret_data))

        provider = ClusterSecretsProvider(namespace="layer-3-production")
        creds = provider.get_credentials("s3", "layer3", "production")

        assert creds["key"] == "value"
```

**Key Pattern:** Mock `ClusterBase._check_cluster_context()` to bypass the cluster guard:

- Cluster components inherit from `ClusterBase`
- `ClusterBase.__init__()` calls `_check_cluster_context()`
- Tests mock this method with `@patch.object(ClusterBase, '_check_cluster_context')`
- This allows full testing of cluster logic outside Kubernetes

Running cluster tests locally:

```bash
$ uv run pytest tests/cluster/ -v
tests/cluster/test_environment.py::test_init_reads_current_namespace PASSED
tests/cluster/test_environment.py::test_get_environment_production PASSED
tests/cluster/test_secrets.py::test_get_credentials_success PASSED
# All 26 cluster tests pass!
```

## Mocking

### Mocking Environment Detection

```python
from unittest.mock import patch

def test_with_mocked_environment():
    """Test with specific environment."""
    with patch("kstack_lib.any.container._context_selector", return_value="local"):
        container = KStackIoCContainer()
        detector = container.environment_detector()
        # detector is now a LocalEnvironmentDetector
```

### Mocking Cloud Services

```python
from unittest.mock import MagicMock

def test_with_mocked_storage():
    """Test with mocked storage adapter."""
    mock_storage = MagicMock()
    mock_storage.upload_file.return_value = {"ETag": "test123"}

    # Inject mock into container
    container = KStackIoCContainer()
    container.cloud_storage_adapter.override(mock_storage)
```

### Mocking File System

```python
from unittest.mock import mock_open, patch

def test_config_file_reading():
    """Test config file reading with mocked file system."""
    mock_content = '{"key": "value"}'

    with patch("builtins.open", mock_open(read_data=mock_content)):
        config = load_config("test.json")
        assert config["key"] == "value"
```

## Testing Services That Use KStack-lib

### Example: Testing a Service Using S3

```python
# my_service.py
from kstack_lib import get_cloud_storage_adapter

class DataService:
    def __init__(self):
        self.storage = get_cloud_storage_adapter(service="s3")

    def save_data(self, key: str, data: bytes):
        self.storage.upload_file(bucket="my-bucket", key=key, body=data)
```

```python
# test_my_service.py
from unittest.mock import MagicMock, patch

def test_data_service():
    """Test DataService with mocked storage."""
    mock_storage = MagicMock()

    with patch("my_service.get_cloud_storage_adapter", return_value=mock_storage):
        service = DataService()
        service.save_data("test.txt", b"data")

        mock_storage.upload_file.assert_called_once_with(
            bucket="my-bucket",
            key="test.txt",
            body=b"data"
        )
```

## Test Fixtures

### Common Fixtures

Create reusable fixtures in `tests/conftest.py`:

```python
# tests/conftest.py
import pytest
from kstack_lib import get_cloud_storage_adapter

@pytest.fixture
def storage_adapter():
    """Provide S3 storage adapter."""
    return get_cloud_storage_adapter(service="s3")

@pytest.fixture
def test_bucket():
    """Provide test bucket name."""
    return "test-bucket"

@pytest.fixture
def setup_test_bucket(storage_adapter, test_bucket):
    """Create and clean up test bucket."""
    # Setup
    try:
        storage_adapter.create_bucket(bucket=test_bucket)
    except Exception:
        pass  # Bucket may already exist

    yield test_bucket

    # Teardown
    try:
        storage_adapter.delete_bucket(bucket=test_bucket, force=True)
    except Exception:
        pass
```

Use in tests:

```python
def test_s3_operations(storage_adapter, setup_test_bucket):
    """Test S3 operations with clean bucket."""
    bucket = setup_test_bucket

    storage_adapter.upload_file(bucket=bucket, key="test.txt", body=b"data")
    response = storage_adapter.download_file(bucket=bucket, key="test.txt")
    assert response["Body"].read() == b"data"
```

## Coverage

Current coverage: **58.52%**

Modules not covered:

- **Cluster modules** (93 lines): Cannot be unit tested outside K8s - require integration tests in actual cluster
- **Deprecated modules**: Old code pending deletion (vault.py, utils/, config/secrets.py old patterns)

Target: Keep coverage above 58% for testable code.

View coverage report:

```bash
make test-cov
```

## Continuous Integration

Tests run automatically on every push via GitHub Actions:

```yaml
# .github/workflows/test.yml
- name: Run tests
  run: uv run pytest tests/ --cov=kstack_lib --cov-report=xml
```

## Best Practices

1. **Test behavior, not implementation** - Test what the code does, not how it does it
2. **Use descriptive test names** - `test_upload_file_creates_object` not `test_1`
3. **One assertion per test** - Keeps tests focused and failures clear
4. **Use fixtures for setup** - Avoid repeating setup code
5. **Mock external dependencies** - Don't rely on external services in unit tests
6. **Test edge cases** - Empty inputs, missing files, network errors, etc.
7. **Keep tests fast** - Unit tests should run in milliseconds, not seconds

## Debugging Tests

### Run with verbose output

```bash
uv run pytest tests/ -vv
```

### Show print statements

```bash
uv run pytest tests/ -s
```

### Stop on first failure

```bash
uv run pytest tests/ -x
```

### Run last failed tests

```bash
uv run pytest tests/ --lf
```

### Drop into debugger on failure

```bash
uv run pytest tests/ --pdb
```

## Common Issues

### Import Errors

If you see `KStackEnvironmentError: Cannot import cluster module outside Kubernetes cluster`:

- This is expected behavior for cluster modules
- Tests should be marked to skip: `pytestmark = pytest.mark.skipif(not is_in_cluster())`

### Service Not Available

If integration tests fail with connection errors:

```bash
# Start LocalStack
docker run -d -p 4566:4566 localstack/localstack

# Start Redis
docker run -d -p 6379:6379 redis
```

### Vault Not Decrypted

If you see `VaultDecryptionError`:

```bash
# Decrypt vault
partsecrets reveal --team dev
```
