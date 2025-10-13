#!/usr/bin/env python3
"""
Example: Using CAL (Cloud Abstraction Layer) for S3 operations.

This example demonstrates how to use the Cloud Abstraction Layer to interact
with S3-compatible storage (LocalStack in development, real S3 in production).

The CAL provides:
- Provider-agnostic API (works with LocalStack, AWS S3, DigitalOcean Spaces)
- Automatic configuration from vault and config files
- Auto-discovery of environment from .kstack.yaml
- External access support via Traefik

Requirements:
- Run from kstack-lib or partsnap-kstack directory (or subdirectory)
- .kstack.yaml must exist (auto-discovered in parent dirs)
- Layer 3 (Global Infrastructure) must be deployed
- LocalStack must be accessible at localstack.dev.partsnap.local:31000

Usage:
    cd /home/lbrack/github/devops/kstack-lib
    python examples/layer3/s3_operations.py
"""

from io import BytesIO

from kstack_lib.cal import CloudContainer
from kstack_lib.config import ConfigMap, KStackLayer
from kstack_lib.local.config.environment import LocalEnvironmentDetector


def main() -> None:
    """Demonstrate S3 operations using CAL."""
    print("=" * 80)
    print("Cloud Abstraction Layer - S3 Operations Example")
    print("=" * 80)

    # Step 1: Auto-detect environment and paths
    print("\n📋 Step 1: Auto-detect environment")
    try:
        env_detector = LocalEnvironmentDetector()
        environment = env_detector.get_environment()
        config_root = env_detector.get_config_root()
        vault_root = env_detector.get_vault_root()

        print(f"   Environment: {environment} (from .kstack.yaml)")
        print(f"   Config root: {config_root}")
        print(f"   Vault root: {vault_root}")
    except Exception as e:
        print(f"\n❌ Error: {e}")
        print("\n💡 Make sure you're running from kstack-lib or partsnap-kstack directory")
        print("   and .kstack.yaml exists with: environment: dev")
        return

    # Step 2: Create ConfigMap for Layer 3
    print("\n📋 Step 2: Create ConfigMap")
    cfg = ConfigMap(layer=KStackLayer.LAYER_3_GLOBAL_INFRA)
    print(f"   Layer: {cfg.layer.display_name}")
    print(f"   Namespace: {cfg.layer.namespace}")

    # Step 3: Create CloudContainer with LocalStack provider
    print("\n☁️  Step 3: Create CloudContainer")
    print("   Provider: localstack (auto-configured)")
    print("   Access: External via Traefik (localstack.dev.partsnap.local:31000)")

    try:
        with CloudContainer(
            config=cfg, config_root=config_root, vault_root=vault_root, default_provider="localstack"
        ) as cloud:
            print("   ✓ CloudContainer created successfully")

            # Step 4: Get ObjectStorage service
            print("\n💾 Step 4: Get ObjectStorage service")
            storage = cloud.object_storage(provider="localstack")
            print("   ✓ ObjectStorage service obtained")

            # Step 5: Create a test bucket
            bucket_name = "example-bucket"
            print(f"\n🗑️  Step 5: Create bucket '{bucket_name}'")
            try:
                storage.create_bucket(bucket_name)
                print(f"   ✓ Bucket '{bucket_name}' created")
            except Exception as e:
                if "BucketAlreadyOwnedByYou" in str(e) or "BucketAlreadyExists" in str(e):
                    print(f"   ℹ️  Bucket '{bucket_name}' already exists")
                else:
                    raise

            # Step 6: Upload an object
            object_key = "test-file.txt"
            content = b"Hello from CAL! This is a test file."
            print(f"\n📤 Step 6: Upload object '{object_key}'")
            storage.upload_object(
                bucket_name=bucket_name, object_key=object_key, file_obj=BytesIO(content), content_type="text/plain"
            )
            print(f"   ✓ Uploaded {len(content)} bytes")

            # Step 7: List objects in bucket
            print("\n📋 Step 7: List objects in bucket")
            objects = storage.list_objects(bucket_name=bucket_name)
            print(f"   ✓ Found {len(objects)} objects:")
            for obj in objects:
                print(f"     - {obj['Key']} ({obj.get('Size', 0)} bytes)")

            # Step 8: Download object
            print(f"\n📥 Step 8: Download object '{object_key}'")
            downloaded = storage.download_object(bucket_name=bucket_name, object_key=object_key)
            if downloaded:
                print(f"   ✓ Downloaded {len(downloaded)} bytes")
                print(f"   Content: {downloaded.decode()}")
            else:
                print("   ✗ Object not found or empty")

            # Step 9: Generate presigned URL
            print("\n🔗 Step 9: Generate presigned URL")
            url = storage.generate_presigned_url(bucket_name=bucket_name, object_key=object_key, expiration=3600)
            print("   ✓ Presigned URL generated (valid for 1 hour)")
            print(f"   URL: {url[:80]}...")

            # Check if URL uses external domain
            if "localstack.dev.partsnap.local" in url:
                print("   ✅ URL uses external domain (accessible from browser)")
            else:
                print("   ⚠️  URL uses internal DNS")

            # Step 10: Cleanup
            print("\n🧹 Step 10: Cleanup")
            storage.delete_object(bucket_name=bucket_name, object_key=object_key)
            print("   ✓ Object deleted")

            storage.delete_bucket(bucket_name)
            print("   ✓ Bucket deleted")

    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback

        traceback.print_exc()
        return

    print("\n" + "=" * 80)
    print("✅ All S3 operations completed successfully!")
    print("=" * 80)


if __name__ == "__main__":
    main()
