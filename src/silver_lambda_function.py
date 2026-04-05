import os
import json
import logging
import urllib.parse
from datetime import datetime
import boto3
from botocore.exceptions import ClientError
import requests
import time

logger = logging.getLogger()
logger.setLevel(logging.INFO)

S3_BRONZE_BUCKET = "bronze-lake-kajinmo-xyz"
S3_SILVER_BUCKET = "silver-lake-kajinmo-xyz"
SSM_PARAM_NAME = "etl_bronze_github_token"
REGION_NAME = "us-east-1"

# WARM-START CACHING (Saves money and prevents 403 Rate Limits)
ssm_client = boto3.client('ssm', region_name=REGION_NAME)
s3_client = boto3.client('s3', region_name=REGION_NAME)

# In-memory dictionary to store user locations across executions within the same container
user_location_cache = {}

def get_github_token() -> str:
    """Fetches the GitHub PAT securely from AWS SSM Parameter Store."""
    try:
        response = ssm_client.get_parameter(Name=SSM_PARAM_NAME, WithDecryption=True)
        return response['Parameter']['Value']
    except ClientError as e:
        logger.error(f"Failed to fetch token from SSM: {e}")
        raise

def fetch_user_location(user_url: str, token: str) -> str:
    """Hits the GitHub User API to extract their location, utilizing the ephemeral cache."""
    # 1. Check container ephemeral cache first
    if user_url in user_location_cache:
        logger.debug(f"CACHE HIT for user: {user_url}")
        return user_location_cache[user_url]
        
    # 2. Cache Miss -> Ask Github
    logger.debug(f"CACHE MISS. Fetching from GitHub: {user_url}")
    headers = {
        "Authorization": f"Bearer {token}",
        "Accept": "application/vnd.github.v3+json",
        "X-GitHub-Api-Version": "2022-11-28"
    }
    
    try:
        # Give GitHub a fast 200ms sleep to avoid blasting rate limits
        time.sleep(0.2)
        resp = requests.get(user_url, headers=headers, timeout=5)
        
        if resp.status_code == 404:
            val = "Unknown (404)"
            # Rate Limiting BackOff
        elif resp.status_code == 403:
            logger.warning(f"Rate Limiting hit trying to fetch user location. Pausing...")
            # If hit rate limit, we just back-off and assign Unknown for this batch.
            val = "Unknown (Rate Limited)"
        else:
            resp.raise_for_status()
            user_data = resp.json()
            val = user_data.get("location", "Not Specified")
            if not val:
                val = "Not Specified"
        
        # 3. Store in cache for future iterations
        user_location_cache[user_url] = val
        return val
        
    except requests.exceptions.RequestException as e:
        logger.warning(f"Network error fetching user {user_url}: {e}")
        return "Unknown (Error)"

def lambda_handler(event, context):
    logger.info("--- [START] PIPELINE SILVER GITHUB (ENRICHMENT) ---")
    
    try:
        # The triggering payload from S3 Event Notifications comes inside 'Records'
        for record in event.get('Records', []):
            bucket_name = record['s3']['bucket']['name']
            
            # Key can contain URL-encoded characters (like %3D instead of =)
            object_key = urllib.parse.unquote_plus(record['s3']['object']['key'])
            
            logger.info(f"Processing object: s3://{bucket_name}/{object_key}")
            
            # Step 1: Download raw JSON from Bronze Lake
            try:
                response = s3_client.get_object(Bucket=bucket_name, Key=object_key)
                file_content = response['Body'].read().decode('utf-8')
                raw_events = json.loads(file_content)
            except ClientError as e:
                logger.error(f"Error accessing s3://{bucket_name}/{object_key}: {e}")
                continue
            
            if not raw_events:
                logger.info("Empty array found in Bronze. Skipping.")
                continue

            # Step 2: Enrichment Phase
            token = get_github_token()
            enriched_events = []
            
            for ev in raw_events:
                actor_url = ev.get('actor', {}).get('url')
                if actor_url:
                    location = fetch_user_location(actor_url, token)
                    ev['actor']['location'] = location
                else:
                    ev['actor'] = ev.get('actor', {})
                    ev['actor']['location'] = "Not Found (No URL)"
                
                enriched_events.append(ev)
                
            logger.info(f"Successfully enriched {len(enriched_events)} events.")
            
            # Step 3: Load to Silver Layer (OBT - One Big Table paradigm)
            # We keep the exact same Hive Partition key layout.
            try:
                s3_client.put_object(
                    Bucket=S3_SILVER_BUCKET,
                    Key=object_key,
                    Body=json.dumps(enriched_events, ensure_ascii=False),
                    ContentType="application/json"
                )
                logger.info(f"Saved enriched data to s3://{S3_SILVER_BUCKET}/{object_key}")
            except ClientError as e:
                logger.error(f"Failed to write to Silver Bucket: {e}")
                raise
                
    except Exception as general_error:
        logger.error(f"SILVER PIPELINE CRITICAL FAILURE: {general_error}")
        raise general_error
        
    logger.info("--- [END] PIPELINE SILVER GITHUB ---")
    return {"statusCode": 200, "body": "Silver pipeline execution successful"}
