# Clients API Reference

API documentation for client factories.

## Redis Client

::: kstack_lib.clients.redis.create_redis_client
options:
show_root_heading: true
show_source: true

::: kstack_lib.clients.redis.get_redis_client
options:
show_root_heading: true
show_source: true

??? example "Using Redis Clients"

````python
from kstack_lib.clients import create_redis_client, get_redis_client

    # Method 1: Create new client (factory function)
    redis_raw = create_redis_client("part-raw")
    redis_raw.set("key", "value")

    # Method 2: Get cached singleton client
    redis_cached = get_redis_client("part-raw")
    value = redis_cached.get("key")

    # Working with both databases
    redis_raw = get_redis_client("part-raw")
    redis_audit = get_redis_client("part-audit")

    # Store data
    redis_raw.json().set("part:123", "$", {
        "name": "Widget",
        "price": 9.99
    })

    # Store audit log
    redis_audit.json().set("audit:456", "$", {
        "user": "john",
        "action": "update",
        "part_id": "123"
    })
    ```

## LocalStack Client

::: kstack_lib.clients.localstack.create_localstack_client
options:
show_root_heading: true
show_source: true

::: kstack_lib.clients.localstack.get_localstack_client
options:
show_root_heading: true
show_source: true

??? example "Using LocalStack Clients"
```python
from kstack_lib.clients import create_localstack_client, get_localstack_client

    # Method 1: Create new S3 client
    s3 = create_localstack_client("s3")
    s3.create_bucket(Bucket="my-bucket")

    # Method 2: Get cached client
    s3_cached = get_localstack_client("s3")
    s3_cached.list_buckets()

    # Different AWS services
    sqs = get_localstack_client("sqs")
    queue_url = sqs.create_queue(QueueName="my-queue")

    dynamodb = get_localstack_client("dynamodb")
    tables = dynamodb.list_tables()
    ```
````
