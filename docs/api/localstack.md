# LocalStack API Reference

LocalStack service discovery and AWS client configuration utilities.

## Overview

KStack provides automatic LocalStack discovery and configuration. The library can detect LocalStack instances and provide AWS client configurations that work seamlessly in both local development and Kubernetes environments.

## get_localstack_config

Get LocalStack connection configuration.

::: kstack_lib.config.localstack.get_localstack_config
options:
show_root_heading: true
show_source: true

### Usage

```python
from kstack_lib.config import get_localstack_config

# Get LocalStack configuration
config = get_localstack_config()

print(f"Endpoint: {config['endpoint_url']}")
print(f"Region: {config['region_name']}")
```

### Parameters

- **route** (str, optional): The route to use. Defaults to current active route.
- **layer** (KStackLayer, optional): The layer to search in. Defaults to Layer 3.

### Returns

Dictionary with keys:

- `endpoint_url`: LocalStack endpoint URL
- `region_name`: AWS region name (typically "us-east-1")
- `aws_access_key_id`: Access key (for LocalStack)
- `aws_secret_access_key`: Secret key (for LocalStack)

### Example: Using with boto3

```python
from kstack_lib.config import get_localstack_config
import boto3

# Get LocalStack configuration
config = get_localstack_config()

# Create S3 client
s3 = boto3.client('s3', **config)

# Use the client
buckets = s3.list_buckets()
print(f"Buckets: {buckets['Buckets']}")
```

## Using boto3 with LocalStack

Once you have the LocalStack configuration, you can use it with boto3:

```python
from kstack_lib.config import get_localstack_config
import boto3

# Get configuration
config = get_localstack_config()

# Create boto3 clients
s3 = boto3.client('s3', **config)
dynamodb = boto3.client('dynamodb', **config)
sqs = boto3.client('sqs', **config)

# Use the clients
s3.list_buckets()
dynamodb.list_tables()
sqs.list_queues()
```

## Supported AWS Services

Common AWS services supported by LocalStack:

| Service         | boto3 Name       | Purpose              |
| --------------- | ---------------- | -------------------- |
| S3              | `s3`             | Object storage       |
| DynamoDB        | `dynamodb`       | NoSQL database       |
| SQS             | `sqs`            | Message queues       |
| SNS             | `sns`            | Notifications        |
| Lambda          | `lambda`         | Serverless functions |
| CloudWatch      | `cloudwatch`     | Monitoring           |
| Secrets Manager | `secretsmanager` | Secret storage       |
| Systems Manager | `ssm`            | Parameter store      |

## Best Practices

### ✅ DO: Use get_localstack_config for Automatic Configuration

```python
from kstack_lib.config import get_localstack_config
import boto3

# Get configuration
config = get_localstack_config()

# Create client - works in both local and K8s
s3 = boto3.client('s3', **config)
```

### ❌ DON'T: Hardcode LocalStack Endpoints

```python
# Avoid this - won't work in different environments
s3 = boto3.client(
    's3',
    endpoint_url='http://localhost:4566',
    region_name='us-east-1'
)
```

### ✅ DO: Handle Service Availability

```python
from kstack_lib.config import get_localstack_config
import boto3
from botocore.exceptions import BotoCoreError

try:
    config = get_localstack_config()
    s3 = boto3.client('s3', **config)
    s3.list_buckets()
except BotoCoreError as e:
    print(f"AWS service unavailable: {e}")
```

### ✅ DO: Use Environment-Aware Code

```python
from kstack_lib.config import ConfigMap, get_localstack_config
import boto3

cfg = ConfigMap()
route = cfg.get_active_route()

if route == "development":
    # LocalStack in development
    config = get_localstack_config()
    s3 = boto3.client('s3', **config)
elif route == "production":
    # Real AWS in production
    s3 = boto3.client('s3')  # Uses AWS credentials
```

## Environment Detection

KStack automatically detects the environment:

- **Local Development**: Uses LocalStack at `http://localstack:4566`
- **Kubernetes**: Uses LocalStack service in `layer-3-cloud` namespace
- **Production**: Can be configured to use real AWS services

## See Also

- [Configuration API](config.md) - Main configuration utilities
- [Redis API](redis.md) - Redis service discovery
- [LocalStack Client Guide](../guide/localstack-client.md) - User guide for LocalStack
