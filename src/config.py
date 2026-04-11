import os
import logging

# --- Logging Configuration ---
logger = logging.getLogger()
logger.setLevel(logging.INFO)

# --- Environment Variables ---
S3_BRONZE_BUCKET = os.getenv("S3_BRONZE_BUCKET", "bronze-lake-kajinmo-xyz")
S3_SILVER_BUCKET = os.getenv("S3_SILVER_BUCKET", "silver-lake-kajinmo-xyz")
REGION_NAME = os.getenv("REGION_NAME", "us-east-1")
SSM_PARAM_NAME = os.getenv("SSM_PARAM_NAME", "etl_github_token")
GITHUB_EVENTS_URL = os.getenv("GITHUB_EVENTS_URL", "https://api.github.com/events")
