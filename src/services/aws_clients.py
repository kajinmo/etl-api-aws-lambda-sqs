import boto3
import json
import logging
from datetime import datetime, timezone
from botocore.exceptions import ClientError
from typing import List, Dict, Any
import os

logger = logging.getLogger()

# Initializing clients outside the handler helps caching
REGION_NAME = os.getenv("REGION_NAME", "us-east-1")
ssm_client = boto3.client('ssm', region_name=REGION_NAME)
s3_client = boto3.client('s3', region_name=REGION_NAME)

def get_ssm_token(param_name: str) -> str:
    """Fetches the GitHub PAT securely from AWS SSM Parameter Store."""
    try:
        response = ssm_client.get_parameter(
            Name=param_name,
            WithDecryption=True
        )
        return response['Parameter']['Value']
    except ClientError as e:
        logger.error(f"Failed to fetch token from SSM ({param_name}): {e}")
        # A failure here must stop the ETL execution
        raise

def load_bronze_layer_s3(data: List[Dict[str, Any]], bucket: str) -> str:
    """Loads data into S3 adopting a Hive Partition pattern."""
    now = datetime.now(timezone.utc)
    # Creating Hive format: year=YYYY/month=MM/day=DD
    partition = f"year={now.strftime('%Y')}/month={now.strftime('%m')}/day={now.strftime('%d')}"
    file_name = f"events_{now.strftime('%H%M%S')}.json"
    
    s3_key = f"github_events/{partition}/{file_name}"
    
    logger.info(f"Uploading to data lake (S3) -> s3://{bucket}/{s3_key}")
    
    try:
        s3_client.put_object(
            Bucket=bucket,
            Key=s3_key,
            Body=json.dumps(data, ensure_ascii=False),
            ContentType="application/json"
        )
        logger.info("Load consolidated into the Bronze layer successfully.")
        return s3_key
    except ClientError as e:
        logger.error(f"Fatal AWS Error attempting to load S3: {e}")
        raise

def read_json_from_s3(bucket: str, key: str) -> List[Dict[str, Any]]:
    """Reads and parses a JSON file from S3."""
    try:
        response = s3_client.get_object(Bucket=bucket, Key=key)
        file_content = response['Body'].read().decode('utf-8')
        return json.loads(file_content)
    except ClientError as e:
        logger.error(f"Error accessing s3://{bucket}/{key}: {e}")
        raise

def load_silver_layer_s3(data: List[Dict[str, Any]], bucket: str, key: str) -> None:
    """Loads transformed data into Silver S3 layer using the original object key."""
    try:
        s3_client.put_object(
            Bucket=bucket,
            Key=key,
            Body=json.dumps(data, ensure_ascii=False),
            ContentType="application/json"
        )
        logger.info(f"Saved enriched data to s3://{bucket}/{key}")
    except ClientError as e:
        logger.error(f"Failed to write to Silver Bucket: {e}")
        raise
