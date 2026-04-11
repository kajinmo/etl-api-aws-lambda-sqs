import urllib.parse

from config import S3_SILVER_BUCKET, SSM_PARAM_NAME, logger
from services.aws_clients import get_ssm_token, read_json_from_s3, load_silver_layer_s3
from services.github_api import fetch_user_location

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
                raw_events = read_json_from_s3(bucket_name, object_key)
            except Exception:
                continue # Error is logged in the service module
            
            if not raw_events:
                logger.info("Empty array found in Bronze. Skipping.")
                continue

            # Step 2: Enrichment Phase
            token = get_ssm_token(SSM_PARAM_NAME)
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
            load_silver_layer_s3(enriched_events, S3_SILVER_BUCKET, object_key)
                
    except Exception as general_error:
        logger.error(f"SILVER PIPELINE CRITICAL FAILURE: {general_error}")
        raise general_error
        
    logger.info("--- [END] PIPELINE SILVER GITHUB ---")
    return {"statusCode": 200, "body": "Silver pipeline execution successful"}
