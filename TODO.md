# kstack-lib TODO

## Testing

### LocalStack Client Test Coverage

**Status:** Deferred
**Priority:** Low
**Created:** 2025-10-07

**Issue:**
LocalStack client tests (12 tests in `tests/test_localstack_client.py`) are currently skipped in CI/CD because boto3 and aioboto3 are optional dependencies. The entire module is skipped via `pytest.importorskip()` when these packages aren't installed.

**Current Behavior:**

- ✅ Tests pass locally when boto3/aioboto3 are installed
- ⚠️ Tests skipped in CI/CD (boto3/aioboto3 not in base dependencies)
- ✅ Skip is intentional and documented

**Future Improvement Options:**

1. **Add boto3/aioboto3 as dev dependencies** (recommended)

   - Install in CI for testing
   - Keep as optional for production installs
   - Ensures LocalStack functionality is tested

2. **Integration tests with actual LocalStack**

   - Spin up LocalStack container in CI
   - Test against real LocalStack instance
   - More comprehensive but slower

3. **Mock without importing boto3**
   - Restructure tests to avoid importing boto3/aioboto3
   - More complex test setup
   - Less realistic testing

**References:**

- Test file: `tests/test_localstack_client.py`
- Implementation: `kstack_lib/clients/localstack.py`
- CI workflow: `.github/workflows/main.yml`

**Decision:** Skipped for now to maintain fast CI/CD. LocalStack is an optional feature and less critical than core Redis/secrets functionality. Will revisit when LocalStack usage increases.
