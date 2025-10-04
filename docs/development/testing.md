# Testing

Comprehensive testing guide for kstack-lib.

## Test Structure

```
tests/
├── __init__.py
├── test_redis_client.py      # Redis client tests
├── test_redis_config.py       # Redis config tests
├── test_localstack_client.py  # LocalStack client tests
└── test_localstack_config.py  # LocalStack config tests
```

## Running Tests

### All Tests

```bash
uv run pytest tests/ -v -m unit
```

### Specific Test File

```bash
uv run pytest tests/test_redis_client.py -v
```

### Specific Test Function

```bash
uv run pytest tests/test_redis_client.py::test_create_sync_redis_client_part_raw -v
```

### With Coverage

```bash
uv run pytest tests/ -v -m unit \
  --cov=kstack_lib \
  --cov-report=term \
  --cov-report=html
```

View HTML coverage report:
```bash
open htmlcov/index.html
```

## Test Categories

### Unit Tests

Fast tests with no external dependencies. All external services are mocked.

```python
@pytest.mark.unit
def test_create_sync_redis_client():
    with patch('kstack_lib.clients.redis.get_redis_config') as mock_config:
        mock_config.return_value = {
            "host": "localhost",
            "port": 6379,
            "username": "default",
            "password": "test"
        }
        # Test implementation...
```

### Integration Tests (Future)

Tests that require real infrastructure:

```python
@pytest.mark.integration
async def test_real_redis_connection():
    redis = create_redis_client(database='part-raw')
    await redis.set('test-key', 'test-value')
    value = await redis.get('test-key')
    assert value == 'test-value'
```

Run only unit tests (CI/CD):
```bash
uv run pytest tests/ -v -m unit
```

Run integration tests (manual):
```bash
uv run pytest tests/ -v -m integration
```

## Test Fixtures

### Temporary Vault Files

```python
@pytest.fixture
def temp_vault_file(tmp_path):
    """Create temporary vault file for testing."""
    vault_dir = tmp_path / "vault" / "dev"
    vault_dir.mkdir(parents=True)

    vault_data = {
        "development": {
            "part-raw": {
                "host": "redis-development.local",
                "port": 6379,
                "username": "default",
                "password": "test"
            }
        }
    }

    vault_file = vault_dir / "redis-cloud.yaml"
    with open(vault_file, "w") as f:
        yaml.dump(vault_data, f)

    return tmp_path
```

## Mocking

### Mock Configuration

```python
from unittest.mock import patch, MagicMock

@patch('kstack_lib.config.redis.get_redis_config')
def test_with_mock_config(mock_config):
    mock_config.return_value = {
        "host": "localhost",
        "port": 6379,
        "username": "default",
        "password": "test"
    }
    # Test code...
```

### Mock Redis Client

```python
@patch('redis.Redis')
def test_redis_operations(mock_redis):
    mock_client = MagicMock()
    mock_redis.return_value = mock_client
    mock_client.get.return_value = b'{"key": "value"}'

    # Test code...
    mock_client.get.assert_called_once_with('test-key')
```

### Mock Kubernetes

```python
@patch('subprocess.run')
def test_kubernetes_configmap(mock_run):
    mock_result = MagicMock(returncode=0, stdout="development")
    mock_run.return_value = mock_result

    # Test code...
```

## Coverage Requirements

Minimum coverage: 80%

Current coverage:
- `kstack_lib/clients/redis.py`: 100%
- `kstack_lib/clients/localstack.py`: 100%
- `kstack_lib/config/redis.py`: 100%
- `kstack_lib/config/localstack.py`: 100%

## Continuous Integration

Tests run automatically on:
- Every push to main
- Every pull request
- Manual workflow dispatch

See `.github/workflows/test.yml` for CI configuration.

## Best Practices

1. **Mock all external dependencies** - Redis, Kubernetes, file system
2. **Test both success and failure paths**
3. **Test edge cases** - empty config, missing files, network errors
4. **Use descriptive test names** - `test_create_sync_redis_client_part_raw`
5. **Keep tests fast** - Mock slow operations
6. **Test async and sync separately** - Different code paths
7. **Clean up resources** - Use fixtures with proper teardown
