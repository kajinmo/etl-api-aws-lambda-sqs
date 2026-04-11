import json
import logging
from pydantic import ValidationError

# Isolated Modules
from config import S3_BRONZE_BUCKET, SSM_PARAM_NAME, GITHUB_EVENTS_URL, logger
from models import GithubEvent
from services.aws_clients import get_ssm_token, load_bronze_layer_s3
from services.github_api import fetch_public_events

# --- Dispatch Function (Main) ---
def lambda_handler(event, context):
    """Entry point triggered by AWS Lambda."""
    logger.info("--- [START] PIPELINE BRONZE GITHUB ---")
    
    try:
        # Step 1: Security, fetch master key via AWS Service Module
        token = get_ssm_token(SSM_PARAM_NAME)
        
        # Step 2: Raw extraction via API Service Module
        raw_events = fetch_public_events(token, GITHUB_EVENTS_URL)
        
        if not raw_events:
            logger.warning("No events returned from API. Ending data flow prematurely.")
            return {"statusCode": 200, "body": "No new events from API."}
            
        # Step 3: Pydantic Validation Filter (via Models Module)
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
        
        # Step 4: Loading the Lake (via AWS Service Module)
        if valid_events:
            saved_key = load_bronze_layer_s3(valid_events, S3_BRONZE_BUCKET)
            message = "Batch loaded successfully into S3."
        else:
            message = "0 records validated. No load required."
            saved_key = "None"
            
        logger.info("--- [END] Pipeline Executed Successfully ---")
        
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
    # If script runs locally, basic config makes sure `logger.info` outputs to terminal
    logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
    logger.info("Executing Lambda Locally...")
    
    mock_event = {}
    mock_context = None
    
    result = lambda_handler(mock_event, mock_context)
    print(f"Local Result: {result}")
