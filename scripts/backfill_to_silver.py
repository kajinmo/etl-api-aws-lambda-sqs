import boto3
import json
import logging
from concurrent.futures import ThreadPoolExecutor

# Set up raw terminal logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

BRONZE_BUCKET = "bronze-lake-kajinmo-xyz"
SILVER_LAMBDA_NAME = "etl_github_events_silver_enricher"
REGION = "us-east-1"

# We use boto3 default session which relies on local AWS CLI credentials
s3_client = boto3.client('s3', region_name=REGION)
lambda_client = boto3.client('lambda', region_name=REGION)

def mock_s3_event_payload(bucket_name: str, object_key: str) -> dict:
    """
    Creates a simulated S3 Notification event payload so the Silver Layer 
    believes AWS S3 inherently triggered the function.
    """
    return {
        "Records": [
            {
                "eventSource": "aws:s3",
                "eventName": "ObjectCreated:Put",
                "s3": {
                    "bucket": {
                        "name": bucket_name
                    },
                    "object": {
                        "key": object_key
                    }
                }
            }
        ]
    }

def process_key(key: str):
    """Invokes the Silver Lambda asynchronously for a single S3 Key"""
    logger.info(f"Triggering Backfill for: {key}")
    
    payload = mock_s3_event_payload(BRONZE_BUCKET, key)
    
    try:
        # InvocationType='Event' means asynchronous run. The script won't wait for Lambda to finish.
        response = lambda_client.invoke(
            FunctionName=SILVER_LAMBDA_NAME,
            InvocationType='Event', 
            Payload=json.dumps(payload)
        )
        status_code = response.get('StatusCode')
        if status_code == 202: # 202 Accepted applies for Async invoking
            logger.info(f"Successfully queued Lambda for {key}")
        else:
            logger.warning(f"Unexpected status {status_code} invoking Lambda for {key}")
    except Exception as e:
        logger.error(f"Failed invoking Lambda for {key}: {e}")

def run_backfill():
    logger.info(f"Starting Bronze to Silver Backfill scan on bucket: {BRONZE_BUCKET}")
    
    paginator = s3_client.get_paginator('list_objects_v2')
    pages = paginator.paginate(Bucket=BRONZE_BUCKET, Prefix='github_events/')
    
    all_keys = []
    for page in pages:
        if 'Contents' in page:
            for obj in page['Contents']:
                if obj['Key'].endswith('.json'):
                    all_keys.append(obj['Key'])
                    
    total_keys = len(all_keys)
    logger.info(f"Found {total_keys} objects requiring processing.")
    
    if total_keys == 0:
        logger.info("Nothing to backfill. Exiting.")
        return
        
    # We use threads to rapidly dispatch the Lambda triggers.
    with ThreadPoolExecutor(max_workers=10) as executor:
        executor.map(process_key, all_keys)
        
    logger.info("Backfill trigger dispatch completed. Check AWS CloudWatch for enrichment process metrics.")

if __name__ == "__main__":
    run_backfill()
