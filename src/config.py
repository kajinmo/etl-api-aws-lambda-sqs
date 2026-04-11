import os
import logging

# --- Logging Configuration ---
# Setting up standard logger. Best practice to avoid multiple loggers in Lambda.
logger = logging.getLogger()
logger.setLevel(logging.INFO)

# --- Environment Variables ---
# Using os.getenv to fetch variables configured directly in the Lambda Environment.
# We set default values so that local tests won't crash if they are not defined,
# although in production they should always be set via IaC (Terraform).
# 
# How to translate this to Airflow?
# In Airflow, we would use Airflow Variables or Connections to handle these.
S3_BUCKET = os.getenv("S3_BUCKET", "bronze-lake-kajinmo-xyz")
REGION_NAME = os.getenv("REGION_NAME", "us-east-1")
SSM_PARAM_NAME = os.getenv("SSM_PARAM_NAME", "etl_bronze_github_token")
GITHUB_EVENTS_URL = os.getenv("GITHUB_EVENTS_URL", "https://api.github.com/events")
