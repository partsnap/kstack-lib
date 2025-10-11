#!/usr/bin/env python3
"""
Integration tests for Layer 3 LocalStack S3 operations.

Tests the kstack-lib Cloud Abstraction Layer with LocalStack in layer-3-global-infra.
"""

import os
import sys
from io import BytesIO
from pathlib import Path

import pytest

# Ensure kstack-lib is in path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

# Remove AWS_PROFILE to prevent conflicts
os.environ.pop("AWS_PROFILE", None)


@pytest.mark.integration
def test_bucket_operations(localstack):
    """Test 1.1: Basic bucket operations."""
    print("\n" + "=" * 70)
    print("TEST 1.1: Basic Bucket Operations")
    print("=" * 70)

    from kstack_lib.cal import CloudContainer
    from kstack_lib.config import ConfigMap
    from kstack_lib.types import KStackEnvironment, KStackLayer

    cfg = ConfigMap(
        layer=KStackLayer.LAYER_3_GLOBAL_INFRA,
        environment=KStackEnvironment.DEVELOPMENT,
    )

    config_root = Path("/home/lbrack/github/devops/partsnap-kstack")
    vault_root = Path("/home/lbrack/github/devops/partsnap-kstack/vault")
    with CloudContainer(cfg, config_root=config_root, vault_root=vault_root) as container:
        storage = container.object_storage()

        # Test: List buckets
        print("\n1. Listing buckets...")
        buckets = storage.list_buckets()
        print(f"   ✓ Listed {len(buckets)} existing buckets: {buckets}")

        # Test: Create bucket
        test_bucket = "integration-test-bucket"
        print(f"\n2. Creating bucket '{test_bucket}'...")
        try:
            storage.create_bucket(test_bucket)
            print(f"   ✓ Created bucket: {test_bucket}")
        except Exception as e:
            if "BucketAlreadyExists" in str(e) or "BucketAlreadyOwnedByYou" in str(e):
                print("   ⚠ Bucket already exists (cleaning up from previous run)")
            else:
                raise

        # Test: Verify bucket exists
        print("\n3. Verifying bucket exists...")
        buckets = storage.list_buckets()
        assert test_bucket in buckets, f"Bucket {test_bucket} not found in {buckets}"
        print("   ✓ Verified bucket exists in listing")

        # Test: Delete bucket
        print("\n4. Deleting bucket...")
        storage.delete_bucket(test_bucket)
        print("   ✓ Deleted bucket")

        # Verify deletion
        buckets = storage.list_buckets()
        assert test_bucket not in buckets, f"Bucket {test_bucket} still exists after deletion"
        print("   ✓ Verified bucket was deleted")

    print("\n" + "=" * 70)
    print("✓ TEST 1.1 PASSED: Basic Bucket Operations")
    print("=" * 70)


@pytest.mark.integration
def test_object_operations(localstack):
    """Test 1.2: Object upload/download operations."""
    print("\n" + "=" * 70)
    print("TEST 1.2: Object Upload/Download Operations")
    print("=" * 70)

    from kstack_lib.cal import CloudContainer
    from kstack_lib.config import ConfigMap
    from kstack_lib.types import KStackEnvironment, KStackLayer

    cfg = ConfigMap(
        layer=KStackLayer.LAYER_3_GLOBAL_INFRA,
        environment=KStackEnvironment.DEVELOPMENT,
    )

    config_root = Path("/home/lbrack/github/devops/partsnap-kstack")
    vault_root = Path("/home/lbrack/github/devops/partsnap-kstack/vault")
    with CloudContainer(cfg, config_root=config_root, vault_root=vault_root) as container:
        storage = container.object_storage()

        bucket = "test-objects"

        print(f"\n1. Creating bucket '{bucket}'...")
        try:
            storage.create_bucket(bucket)
            print("   ✓ Created bucket")
        except Exception as e:
            if "BucketAlreadyExists" in str(e) or "BucketAlreadyOwnedByYou" in str(e):
                print("   ⚠ Bucket already exists (cleaning up)")
                # Clean up any existing objects
                try:
                    objects = storage.list_objects(bucket)
                    for obj in objects:
                        storage.delete_object(bucket, obj["Key"])
                except Exception:  # noqa: S110
                    pass
            else:
                raise

        # Test: Upload object
        test_data = b"Hello from integration test!"
        print("\n2. Uploading object...")
        storage.upload_object(bucket, "test.txt", file_obj=BytesIO(test_data), content_type="text/plain")
        print(f"   ✓ Uploaded object 'test.txt' ({len(test_data)} bytes)")

        # Test: List objects
        print("\n3. Listing objects...")
        objects = storage.list_objects(bucket)
        print(f"   ✓ Found {len(objects)} objects")
        assert len(objects) == 1, f"Expected 1 object, found {len(objects)}"
        assert objects[0]["Key"] == "test.txt", f"Expected 'test.txt', found {objects[0]['Key']}"
        print(f"   ✓ Object key: {objects[0]['Key']}")
        print(f"   ✓ Object size: {objects[0]['Size']} bytes")

        # Test: Download object
        print("\n4. Downloading object...")
        data = storage.download_object(bucket, "test.txt")
        assert data == test_data, "Downloaded data doesn't match uploaded data"
        print(f"   ✓ Downloaded {len(data)} bytes")
        print("   ✓ Data integrity verified")

        # Test: Get metadata
        print("\n5. Getting object metadata...")
        metadata = storage.get_object_metadata(bucket, "test.txt")
        print(f"   ✓ Content-Length: {metadata['ContentLength']} bytes")
        print(f"   ✓ Content-Type: {metadata['ContentType']}")
        assert metadata["ContentLength"] == len(test_data)
        assert metadata["ContentType"] == "text/plain"

        # Cleanup
        print("\n6. Cleanup...")
        storage.delete_object(bucket, "test.txt")
        print("   ✓ Deleted object")
        storage.delete_bucket(bucket)
        print("   ✓ Deleted bucket")

    print("\n" + "=" * 70)
    print("✓ TEST 1.2 PASSED: Object Upload/Download Operations")
    print("=" * 70)


@pytest.mark.integration
def test_presigned_urls(localstack):
    """Test 1.3: Presigned URL generation and access."""
    print("\n" + "=" * 70)
    print("TEST 1.3: Presigned URL Generation and Access")
    print("=" * 70)

    import requests

    from kstack_lib.cal import CloudContainer
    from kstack_lib.config import ConfigMap
    from kstack_lib.types import KStackEnvironment, KStackLayer

    cfg = ConfigMap(
        layer=KStackLayer.LAYER_3_GLOBAL_INFRA,
        environment=KStackEnvironment.DEVELOPMENT,
    )

    config_root = Path("/home/lbrack/github/devops/partsnap-kstack")
    vault_root = Path("/home/lbrack/github/devops/partsnap-kstack/vault")
    with CloudContainer(cfg, config_root=config_root, vault_root=vault_root) as container:
        storage = container.object_storage()

        bucket = "test-presigned"

        print(f"\n1. Creating bucket '{bucket}'...")
        try:
            storage.create_bucket(bucket)
            print("   ✓ Created bucket")
        except Exception as e:
            if "BucketAlreadyExists" in str(e) or "BucketAlreadyOwnedByYou" in str(e):
                print("   ⚠ Bucket already exists")
            else:
                raise

        # Upload test file
        test_data = b"Presigned URL test content"
        print("\n2. Uploading test file...")
        storage.upload_object(bucket, "presigned-test.txt", file_obj=BytesIO(test_data), content_type="text/plain")
        print(f"   ✓ Uploaded {len(test_data)} bytes")

        # Test: Generate presigned URL
        print("\n3. Generating presigned URL...")
        url = storage.generate_presigned_url(bucket, "presigned-test.txt", expiration=300)
        print("   ✓ Generated presigned URL:")
        print(f"     {url[:100]}...")

        # Test: URL contains correct domain
        print("\n4. Validating URL domain...")
        # For dev machine testing, we use localhost:4566
        # For in-cluster testing, we'd use localstack.dev.partsnap.local
        assert (
            "localhost:4566" in url or "localstack.dev.partsnap.local" in url
        ), f"URL doesn't contain expected domain: {url}"
        if "localhost:4566" in url:
            print("   ✓ URL contains 'localhost:4566' (dev machine mode)")
        else:
            print("   ✓ URL contains 'localstack.dev.partsnap.local' (in-cluster mode)")

        # Test: Access URL from browser/curl
        print("\n5. Testing HTTP access to presigned URL...")
        try:
            response = requests.get(url, timeout=10)
            assert response.status_code == 200, f"Expected 200, got {response.status_code}"
            assert response.content == test_data, "Response content doesn't match uploaded data"
            print(f"   ✓ HTTP GET successful (status: {response.status_code})")
            print(f"   ✓ Content matches ({len(response.content)} bytes)")
        except requests.exceptions.ConnectionError as e:
            print(f"   ✗ Connection failed: {e}")
            print("   ⚠ Make sure kubectl port-forward is running:")
            print("     kubectl port-forward -n layer-3-global-infra svc/localstack 4566:4566")
            raise

        # Cleanup
        print("\n6. Cleanup...")
        storage.delete_object(bucket, "presigned-test.txt")
        storage.delete_bucket(bucket)
        print("   ✓ Cleanup complete")

    print("\n" + "=" * 70)
    print("✓ TEST 1.3 PASSED: Presigned URL Generation and Access")
    print("=" * 70)


@pytest.mark.integration
def test_large_file(localstack):
    """Test 1.4: Large file upload/download."""
    print("\n" + "=" * 70)
    print("TEST 1.4: Large File Upload/Download (10MB)")
    print("=" * 70)

    from kstack_lib.cal import CloudContainer
    from kstack_lib.config import ConfigMap
    from kstack_lib.types import KStackEnvironment, KStackLayer

    cfg = ConfigMap(
        layer=KStackLayer.LAYER_3_GLOBAL_INFRA,
        environment=KStackEnvironment.DEVELOPMENT,
    )

    config_root = Path("/home/lbrack/github/devops/partsnap-kstack")
    vault_root = Path("/home/lbrack/github/devops/partsnap-kstack/vault")
    with CloudContainer(cfg, config_root=config_root, vault_root=vault_root) as container:
        storage = container.object_storage()

        bucket = "test-large-files"

        print(f"\n1. Creating bucket '{bucket}'...")
        try:
            storage.create_bucket(bucket)
            print("   ✓ Created bucket")
        except Exception as e:
            if "BucketAlreadyExists" in str(e) or "BucketAlreadyOwnedByYou" in str(e):
                print("   ⚠ Bucket already exists")
            else:
                raise

        # Create 10MB test file
        file_size = 10 * 1024 * 1024  # 10MB
        print(f"\n2. Creating {file_size / 1024 / 1024:.1f}MB test data...")
        large_data = b"x" * file_size
        print("   ✓ Created test data")

        # Test: Upload large file
        print("\n3. Uploading large file...")
        storage.upload_object(
            bucket, "large.bin", file_obj=BytesIO(large_data), content_type="application/octet-stream"
        )
        print(f"   ✓ Uploaded {file_size / 1024 / 1024:.1f}MB")

        # Test: Download and verify
        print("\n4. Downloading large file...")
        downloaded = storage.download_object(bucket, "large.bin")
        print(f"   ✓ Downloaded {len(downloaded) / 1024 / 1024:.1f}MB")

        print("\n5. Verifying data integrity...")
        assert len(downloaded) == len(large_data), f"Size mismatch: {len(downloaded)} != {len(large_data)}"
        assert downloaded == large_data, "Data doesn't match"
        print("   ✓ Data integrity verified")

        # Cleanup
        print("\n6. Cleanup...")
        storage.delete_object(bucket, "large.bin")
        storage.delete_bucket(bucket)
        print("   ✓ Cleanup complete")

    print("\n" + "=" * 70)
    print("✓ TEST 1.4 PASSED: Large File Upload/Download")
    print("=" * 70)


def main():
    """Run all Layer 3 S3 integration tests."""
    print("\n" + "=" * 70)
    print("LAYER 3 LOCALSTACK S3 INTEGRATION TESTS")
    print("=" * 70)
    print("\nRunning comprehensive S3 tests against LocalStack in layer-3-global-infra")
    print("\nPrerequisites:")
    print("  - LocalStack running in layer-3-global-infra namespace")
    print("  - kubectl port-forward active (for presigned URL test):")
    print("    kubectl port-forward -n layer-3-global-infra svc/localstack 4566:4566")
    print()

    tests = [
        ("Basic Bucket Operations", test_bucket_operations),
        ("Object Upload/Download", test_object_operations),
        ("Presigned URLs", test_presigned_urls),
        ("Large Files (10MB)", test_large_file),
    ]

    passed = 0
    failed = 0
    results = []

    for test_name, test_func in tests:
        try:
            test_func()
            passed += 1
            results.append((test_name, "PASSED", None))
        except Exception as e:
            failed += 1
            results.append((test_name, "FAILED", str(e)))
            print(f"\n✗ TEST FAILED: {test_name}")
            print(f"   Error: {e}")
            import traceback

            traceback.print_exc()

    # Summary
    print("\n" + "=" * 70)
    print("TEST SUMMARY")
    print("=" * 70)

    for test_name, status, error in results:
        symbol = "✓" if status == "PASSED" else "✗"
        print(f"{symbol} {test_name}: {status}")
        if error:
            print(f"  Error: {error[:100]}...")

    print(f"\nTotal: {len(tests)} tests")
    print(f"Passed: {passed}")
    print(f"Failed: {failed}")

    if failed == 0:
        print("\n🎉 ALL TESTS PASSED!")
        return 0
    else:
        print(f"\n❌ {failed} TEST(S) FAILED")
        return 1


if __name__ == "__main__":
    sys.exit(main())
