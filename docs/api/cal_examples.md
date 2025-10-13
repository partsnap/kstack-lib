# Cloud Abstraction Layer (CAL) Examples

The Cloud Abstraction Layer (CAL) provides a unified interface for cloud services that works across different providers (LocalStack, AWS S3, DigitalOcean Spaces, etc.).

## Overview

CAL abstracts away provider-specific details and provides:

- **Provider-agnostic API**: Same code works with LocalStack (dev), AWS S3 (production), or any S3-compatible service
- **Automatic configuration**: Loads settings from config files and vault
- **External access support**: Works with Traefik IngressRoutes and external domains
- **Context manager support**: Automatic resource cleanup

## Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                      Your Application                        │
└──────────────────────┬──────────────────────────────────────┘
                       │
                       ▼
┌─────────────────────────────────────────────────────────────┐
│               CloudContainer (CAL)                           │
│  ┌──────────────────────────────────────────────────────┐  │
│  │  ObjectStorage Protocol                              │  │
│  │  - create_bucket()                                   │  │
│  │  - upload_object()                                   │  │
│  │  - download_object()                                 │  │
│  │  - list_objects()                                    │  │
│  │  - generate_presigned_url()                          │  │
│  │  - delete_object()                                   │  │
│  │  - delete_bucket()                                   │  │
│  └──────────────────────────────────────────────────────┘  │
└──────────────────────┬──────────────────────────────────────┘
                       │
        ┌──────────────┼──────────────┐
        ▼              ▼              ▼
┌─────────────┐ ┌─────────────┐ ┌─────────────┐
│ LocalStack  │ │   AWS S3    │ │ DO Spaces   │
│  Adapter    │ │   Adapter   │ │   Adapter   │
└─────────────┘ └─────────────┘ └─────────────┘
        │              │              │
        ▼              ▼              ▼
┌─────────────┐ ┌─────────────┐ ┌─────────────┐
│ LocalStack  │ │   AWS S3    │ │ DO Spaces   │
│   Server    │ │   Service   │ │   Service   │
└─────────────┘ └─────────────┘ └─────────────┘
```

## External Access Configuration

### LocalStack via Traefik

LocalStack is accessible externally through Traefik IngressRoute:

- **External URL**: `http://localstack.dev.partsnap.local:31000`
- **Access method**: Traefik IngressRoute → LocalStack service
- **Configuration**: `config/providers/localstack.yaml`

```yaml
# config/providers/localstack.yaml
name: localstack
provider_family: aws
provider_implementation: localstack

services:
  s3:
    # External endpoint via Traefik
    endpoint_url: "http://localstack.dev.partsnap.local:31000"
    presigned_url_domain: "localstack.dev.partsnap.local"

  sqs:
    endpoint_url: "http://localstack.dev.partsnap.local:31000"

  secretsmanager:
    endpoint_url: "http://localstack.dev.partsnap.local:31000"

region: us-west-2
verify_ssl: false
```

### Setup Requirements

1. **Add /etc/hosts entry**:

   ```bash
   echo "192.168.49.2 localstack.dev.partsnap.local" | sudo tee -a /etc/hosts
   ```

2. **Verify Traefik is running**:

   ```bash
   kubectl get svc -n layer-3-global-infra traefik-layer-3
   ```

3. **Test LocalStack health**:
   ```bash
   curl http://localstack.dev.partsnap.local:31000/_localstack/health
   ```

## Basic Example: S3 Operations

See [`examples/layer3/s3_operations.py`](../../examples/layer3/s3_operations.py) for a complete working example.

### Step-by-Step Walkthrough

#### 1. Create ConfigMap

The `ConfigMap` tells CAL which layer you're working with:

```python
from kstack_lib.config import ConfigMap, KStackLayer

cfg = ConfigMap(layer=KStackLayer.LAYER_3_GLOBAL_INFRA)
```

This automatically:

- Sets the namespace to `layer-3-global-infra`
- Determines the active route (dev/staging/prod)
- Loads layer-specific configuration

#### 2. Initialize CloudContainer

The `CloudContainer` loads provider configuration and credentials:

```python
from pathlib import Path
from kstack_lib.cal import CloudContainer

config_root = Path("partsnap-kstack/config")
vault_root = Path("partsnap-kstack/vault")

with CloudContainer(
    config=cfg,
    config_root=config_root,
    vault_root=vault_root,
    default_provider="localstack"
) as cloud:
    # Use cloud services here
    pass
```

**What happens internally:**

1. Loads provider config from `config/providers/localstack.yaml`
2. Loads credentials from `vault/dev/layer3/cloud-credentials.yaml`
3. Creates provider-specific adapter (AWS family for LocalStack)
4. Configures boto3 client with external endpoint URL

#### 3. Get ObjectStorage Service

```python
storage = cloud.object_storage(provider="localstack")
```

This returns an `ObjectStorage` implementation that uses the configured provider.

#### 4. Create a Bucket

```python
bucket_name = "my-bucket"
storage.create_bucket(bucket_name)
```

**Behind the scenes:**

- Sends `CreateBucket` request to `http://localstack.dev.partsnap.local:31000`
- LocalStack creates the bucket
- Traefik routes the request through its IngressRoute

#### 5. Upload an Object

```python
from io import BytesIO

content = b"Hello, World!"
storage.upload_object(
    bucket_name="my-bucket",
    object_key="test.txt",
    file_obj=BytesIO(content),
    content_type="text/plain"
)
```

**Parameters:**

- `bucket_name`: Target bucket
- `object_key`: S3 key (path) for the object
- `file_obj`: Binary file-like object
- `content_type`: MIME type (optional)
- `metadata`: Custom metadata dict (optional)

#### 6. List Objects

```python
objects = storage.list_objects(bucket_name="my-bucket")

for obj in objects:
    print(f"{obj['Key']}: {obj['Size']} bytes")
```

**Returns:** List of dicts with keys:

- `Key`: Object key
- `Size`: Size in bytes
- `LastModified`: Timestamp
- `ETag`: Entity tag

#### 7. Download an Object

```python
data = storage.download_object(
    bucket_name="my-bucket",
    object_key="test.txt"
)

print(data.decode())  # b"Hello, World!"
```

**Returns:** Raw bytes of the object content

#### 8. Generate Presigned URL

```python
url = storage.generate_presigned_url(
    bucket_name="my-bucket",
    object_key="test.txt",
    expiration=3600,  # 1 hour
    http_method="GET"
)

print(url)
# http://localstack.dev.partsnap.local:31000/my-bucket/test.txt?...
```

**Key feature:** The URL uses the external domain `localstack.dev.partsnap.local`, making it accessible from:

- Browser on host machine
- Kubernetes pods (via CoreDNS or hosts resolution)
- Any system that can resolve the domain

#### 9. Delete Objects

```python
# Delete single object
storage.delete_object(
    bucket_name="my-bucket",
    object_key="test.txt"
)

# Delete bucket (must be empty)
storage.delete_bucket("my-bucket")
```

## Advanced Topics

### Provider Selection

CAL supports multiple providers. You can specify which one to use:

```python
# Use LocalStack for development
storage_local = cloud.object_storage(provider="localstack")

# Use real AWS S3 for production
storage_aws = cloud.object_storage(provider="aws")

# Use DigitalOcean Spaces
storage_do = cloud.object_storage(provider="digitalocean")
```

The same API works across all providers!

### Automatic Provider Detection

If you set a `default_provider` in CloudContainer, you don't need to specify it:

```python
with CloudContainer(config=cfg, default_provider="localstack") as cloud:
    storage = cloud.object_storage()  # Uses localstack automatically
```

### Error Handling

CAL raises `KStackError` for configuration issues:

```python
from kstack_lib.any.exceptions import KStackError

try:
    storage = cloud.object_storage(provider="unknown")
except KStackError as e:
    print(f"Configuration error: {e}")
```

Provider-specific errors (like boto3 exceptions) are passed through unchanged.

### Context Manager Benefits

Using `with CloudContainer(...) as cloud:` ensures:

1. Resources are properly initialized
2. Connections are cleaned up automatically
3. No resource leaks even if exceptions occur

## Configuration Files

### Provider Configuration

`config/providers/localstack.yaml`:

- Defines endpoint URLs for each service
- Sets region and SSL verification
- Configures service-specific options

### Credentials

`vault/dev/layer3/cloud-credentials.yaml`:

```yaml
providers:
  localstack:
    aws_access_key_id: test
    aws_secret_access_key: test
```

These are loaded automatically by CAL.

### Vault Encryption

The vault can be encrypted with partsecrets. CAL automatically:

1. Detects if vault is encrypted
2. Attempts to decrypt it
3. Uses the decrypted credentials
4. Re-encrypts on cleanup (if it was encrypted initially)

## Testing

Run the example from the partsnap-kstack directory:

```bash
cd /home/lbrack/github/devops/partsnap-kstack
.venv/bin/python ../kstack-lib/examples/layer3/s3_operations.py
```

The example will:

1. Auto-discover the environment from `.kstack.yaml` in the current directory
2. Auto-discover config_root and vault_root (partsnap-kstack directory)
3. Load provider configuration from `providers/localstack.yaml`
4. Load credentials from `vault/dev/layer3/cloud-credentials.yaml`
5. Connect to LocalStack via Traefik at `localstack.dev.partsnap.local:31000`

Expected output:

```
================================================================================
Cloud Abstraction Layer - S3 Operations Example
================================================================================

📋 Step 1: Create ConfigMap
   Layer: Layer 3: Global Infrastructure
   Namespace: layer-3-global-infra

☁️  Step 3: Create CloudContainer
   Provider: localstack
   ✓ CloudContainer created successfully

💾 Step 4: Get ObjectStorage service
   ✓ ObjectStorage service obtained

🗑️  Step 5: Create bucket 'example-bucket'
   ✓ Bucket 'example-bucket' created

📤 Step 6: Upload object 'test-file.txt'
   ✓ Uploaded 37 bytes

📋 Step 7: List objects in bucket
   ✓ Found 1 objects:
     - test-file.txt (37 bytes)

📥 Step 8: Download object 'test-file.txt'
   ✓ Downloaded 37 bytes
   Content: Hello from CAL! This is a test file.

🔗 Step 9: Generate presigned URL
   ✓ Presigned URL generated (valid for 1 hour)
   URL: http://localstack.dev.partsnap.local:31000/example-bucket/test-file.txt...
   ✅ URL uses external domain (accessible from browser)

🧹 Step 10: Cleanup
   ✓ Object deleted
   ✓ Bucket deleted

================================================================================
✅ All S3 operations completed successfully!
================================================================================
```

## Troubleshooting

### "Connection refused" to localstack.dev.partsnap.local

**Problem:** Can't connect to LocalStack

**Solutions:**

1. Check `/etc/hosts` has the entry
2. Verify Traefik is running: `kubectl get pods -n layer-3-global-infra`
3. Test directly: `curl http://localstack.dev.partsnap.local:31000/_localstack/health`

### "The config profile (localstack) could not be found"

**Problem:** boto3 can't find AWS credentials profile

**Solution:** Create `~/.aws/credentials`:

```bash
mkdir -p ~/.aws
cat > ~/.aws/credentials << 'EOF'
[localstack]
aws_access_key_id = test
aws_secret_access_key = test
EOF
```

### Presigned URLs use internal DNS

**Problem:** Generated URLs have `localstack.layer-3-global-infra.svc.cluster.local`

**Solution:** Update `config/providers/localstack.yaml`:

```yaml
services:
  s3:
    endpoint_url: "http://localstack.dev.partsnap.local:31000"
    presigned_url_domain: "localstack.dev.partsnap.local"
```

## See Also

- [CAL Architecture](../architecture/cal-architecture.md)
- [Redis Examples](./redis_examples.md)
- [ConfigMap Guide](../guides/configmaps.md)
