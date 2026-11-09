import os
import json
from dotenv import load_dotenv

# 1. Load local environment variables before importing app modules
load_dotenv()

from handler import lambda_handler

# 2. Mock Lambda context
class MockContext:
    function_name = "local_ingestion_worker"
    memory_limit_in_mb = 256
    invoked_function_arn = "arn:aws:lambda:local:123456789012:function:ingest"
    aws_request_id = "test-request-id-1234"

# 3. Construct synthetic SQS Event payload
mock_sqs_event = {
    "Records": [
        {
            "messageId": "msg-001",
            "receiptHandle": "handle-001",
            "body": json.dumps({
                "topicId": "aws-saa-c03",
                "url": "https://www.cromacampus.com/blogs/quick-reference-guide-for-aws-certified-ai-practitioner/"
            }),
            "attributes": {
                "ApproximateReceiveCount": "1",
                "SentTimestamp": "1700000000000",
                "SenderId": "test-sender",
                "ApproximateFirstReceiveTimestamp": "1700000000001"
            },
            "messageAttributes": {},
            "md5OfBody": "test-md5",
            "eventSource": "aws:sqs",
            "eventSourceARN": "arn:aws:sqs:us-east-1:123456789012:ingestion-task-queue",
            "awsRegion": os.getenv("AWS_REGION", "us-east-1")
        }
    ]
}

if __name__ == "__main__":
    print("🚀 Running local Ingestion Worker simulation...")
    result = lambda_handler(mock_sqs_event, MockContext())
    print("✅ Execution Result:", result)