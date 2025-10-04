# LocalStack Client

Guide to using the LocalStack client factory for AWS service emulation.

## Overview

The LocalStack client factory provides boto3/aioboto3 clients configured for LocalStack endpoints, enabling AWS service emulation in development.

## Basic Usage

### S3 Client

```python
from kstack_lib import create_localstack_client

# Synchronous S3 client
s3 = create_localstack_client('s3')
buckets = s3.list_buckets()

# Create bucket
s3.create_bucket(Bucket='my-bucket')

# Upload file
s3.put_object(
    Bucket='my-bucket',
    Key='file.txt',
    Body=b'Hello World'
)
```

### Async S3 Client

```python
from kstack_lib import create_localstack_client

async def upload_file(data: bytes):
    s3 = create_localstack_client('s3')
    async with s3 as client:
        await client.put_object(
            Bucket='my-bucket',
            Key='file.txt',
            Body=data
        )
```

## Supported Services

All AWS services supported by LocalStack:

- **S3** - Object storage
- **DynamoDB** - NoSQL database
- **RDS** - Relational database
- **SQS** - Message queues
- **SNS** - Notifications
- **Lambda** - Serverless functions
- And more...

```python
# DynamoDB
dynamodb = create_localstack_client('dynamodb')

# SQS
sqs = create_localstack_client('sqs')

# RDS
rds = create_localstack_client('rds')
```

## Configuration Discovery

LocalStack configuration is discovered from:

1. **Local Development** - Vault file:
   ```yaml
   # ~/github/devops/partsnap-kstack/vault/dev/localstack.yaml
   development:
     endpoint_url: http://localhost:4566
     aws_access_key_id: test
     aws_secret_access_key: test
     region_name: us-west-2
   ```

2. **Kubernetes** - Secret:
   ```yaml
   apiVersion: v1
   kind: Secret
   metadata:
     name: localstack-credentials-development
     namespace: layer-3-cloud
   data:
     endpoint-url: aHR0cDovL2xvY2Fsc3RhY2stZGV2ZWxvcG1lbnQubGF5ZXItMy1jbG91ZDo0NTY2
     aws-access-key-id: dGVzdA==
     aws-secret-access-key: dGVzdA==
     region-name: dXMtd2VzdC0y
   ```

## Custom Routes

Specify a custom route:

```python
# Development route (default)
s3_dev = create_localstack_client('s3', route='development')

# Testing route
s3_test = create_localstack_client('s3', route='testing')
```

## Best Practices

1. **Use context managers for async clients**:
   ```python
   s3 = create_localstack_client('s3')
   async with s3 as client:
       await client.list_buckets()
   ```

2. **Handle service errors**:
   ```python
   from botocore.exceptions import ClientError

   try:
       s3.create_bucket(Bucket='my-bucket')
   except ClientError as e:
       if e.response['Error']['Code'] == 'BucketAlreadyExists':
           print("Bucket already exists")
       else:
           raise
   ```

3. **Use resource helpers**:
   ```python
   import boto3

   # Get configured endpoint URL
   config = get_localstack_config()

   # Create resource (higher-level API)
   s3_resource = boto3.resource(
       's3',
       endpoint_url=config['endpoint_url'],
       aws_access_key_id=config['aws_access_key_id'],
       aws_secret_access_key=config['aws_secret_access_key'],
       region_name=config['region_name']
   )
   ```

## API Reference

See [API Documentation](../api/clients.md#localstack-client) for complete reference.
