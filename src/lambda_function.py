import os
import json
import logging
from datetime import datetime, timezone
import boto3
from botocore.exceptions import ClientError
import requests
from pydantic import BaseModel, Field, ValidationError
from typing import Any, Dict, List, Optional

# --- Logging Configuration ---
logger = logging.getLogger()
logger.setLevel(logging.INFO)

# --- Constants Definition ---
S3_BUCKET = "bronze-lake-kajinmo-xyz"
SSM_PARAM_NAME = "etl_bronze_github_token"
REGION_NAME = "us-east-1"
GITHUB_EVENTS_URL = "https://api.github.com/events"

# Initializing clients outside the handler helps caching (Lower Cold Start on AWS)
ssm_client = boto3.client('ssm', region_name=REGION_NAME)
s3_client = boto3.client('s3', region_name=REGION_NAME)

# --- Pydantic Models (Typing and Validation Layer) ---
class GithubActor(BaseModel):
    id: int
    login: str

class GithubRepo(BaseModel):
    id: int
    name: str

class GithubEvent(BaseModel):
    id: str
    type: str # Ex: PushEvent, WatchEvent
    actor: GithubActor
    repo: GithubRepo
    created_at: str
    # Raw payload varies greatly across events, leaving it dynamic
    payload: Optional[Dict[str, Any]] = None

# --- Backend Functions ---
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

def fetch_public_events(token: str) -> List[Dict[str, Any]]:
    """Retrieves public events from GitHub API."""
    headers = {
        "Authorization": f"Bearer {token}",
        "Accept": "application/vnd.github.v3+json",
        "X-GitHub-Api-Version": "2022-11-28"
    }
    logger.info(f"Making extraction request to endpoint: {GITHUB_EVENTS_URL}")
    
    try:
        response = requests.get(GITHUB_EVENTS_URL, headers=headers, timeout=10)
        
        # Strict HTTP Error handling
        if response.status_code == 401:
            logger.error("Request Denied (401). Check the Token in SSM Parameter Store.")
            response.raise_for_status()
        elif response.status_code == 403:
            logger.error("Rate Limit Exceeded (403).")
            response.raise_for_status()
            
        response.raise_for_status()
        return response.json()
    except requests.exceptions.RequestException as e:
        logger.error(f"Communication failure with Github API: {e}")
        raise

def load_bronze_layer_s3(data: List[Dict[str, Any]]) -> str:
    """Loads data into S3 adopting a Hive Partition pattern."""
    now = datetime.now(timezone.utc)
    # Creating Hive format: year=YYYY/month=MM/day=DD
    partition = f"year={now.strftime('%Y')}/month={now.strftime('%m')}/day={now.strftime('%d')}"
    file_name = f"events_{now.strftime('%H%M%S')}.json"
    
    s3_key = f"github_events/{partition}/{file_name}"
    
    logger.info(f"Uploading to data lake (S3) -> s3://{S3_BUCKET}/{s3_key}")
    
    try:
        s3_client.put_object(
            Bucket=S3_BUCKET,
            Key=s3_key,
            Body=json.dumps(data, ensure_ascii=False),
            ContentType="application/json"
        )
        logger.info("Load consolidated into the Bronze layer successfully.")
        return s3_key
    except ClientError as e:
        logger.error(f"Fatal AWS Error attempting to load S3: {e}")
        raise


# --- Dispatch Function (Main) ---
def lambda_handler(event, context):
    """Entry point triggered by AWS Lambda."""
    logger.info("--- [START] PIPELINE BRONZE GITHUB ---")
    
    try:
        # Step 1: Security, fetch master key
        token = get_ssm_token(SSM_PARAM_NAME)
        
        # Step 2: Raw extraction
        raw_events = fetch_public_events(token)
        
        if not raw_events:
            logger.warning("No events returned from API. Ending data flow prematurely.")
            return {"statusCode": 200, "body": "No new events from API."}
            
        # Step 3: Pydantic Validation Filter
        valid_events = []
        for e in raw_events:
            try:
                # Validates typing
                GithubEvent(**e)
                valid_events.append(e)
            except ValidationError as v_err:
                # The API returns junk sometimes, we just skip it
                event_type = e.get("type", "Unknown")
                logger.debug(f"Pydantic Validation failed for type: {event_type}. Reason: {v_err}")
                
        logger.info(f"Initial Extraction: {len(raw_events)} events. Validated by Pydantic: {len(valid_events)}")
        
        # Step 4: Loading the Lake
        if valid_events:
            saved_key = load_bronze_layer_s3(valid_events)
            message = "Batch loaded successfully into S3."
        else:
            message = "0 records validated. No load required."
            saved_key = "None"
            
        logger.info("--- [END] Pipeline Excecuted Successfully ---")
        
        return {
            "statusCode": 200,
            "body": json.dumps({"status": message, "saved_key": saved_key})
        }
        
    except Exception as general_error:
        # Pushing this exception so Lambda understands it crashed.
        # This will queue the payload into the SQS-Dead Letter Queue.
        logger.error(f"PIPELINE FAILED CRITICALLY: {general_error}")
        raise general_error

# --- Local Test Block ---
if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
    logger.info("Executing Lambda Locally...")
    
    mock_event = {}
    mock_context = None
    
    result = lambda_handler(mock_event, mock_context)
    print(f"Local Result: {result}")
