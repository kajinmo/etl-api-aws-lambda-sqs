# Raw storage bucket creation in AWS (Bronze Layer)
resource "aws_s3_bucket" "bronze_lake" {
  bucket = "bronze-lake-kajinmo-xyz"
  
  # Force deletion even if the bucket has objects when running terraform destroy
  force_destroy = true 
}

# Block public access for ultimate security
resource "aws_s3_bucket_public_access_block" "bronze_lake_block" {
  bucket = aws_s3_bucket.bronze_lake.id

  block_public_acls       = true
  block_public_policy     = true
  ignore_public_acls      = true
  restrict_public_buckets = true
}

# Lifecycle policy (Cost protection: Delete objects older than 3 days)
resource "aws_s3_bucket_lifecycle_configuration" "bronze_lake_lifecycle" {
  bucket = aws_s3_bucket.bronze_lake.id

  rule {
    id     = "delete-old-bronze-data-after-3-days"
    status = "Enabled"
    
    filter {
      prefix = ""
    }

    expiration {
      days = 3
    }
  }
}

# ---------------------------------------------
# SILVER LAYER SETUP
# ---------------------------------------------

# Clean/Enriched storage bucket creation in AWS (Silver Layer)
resource "aws_s3_bucket" "silver_lake" {
  bucket = "silver-lake-kajinmo-xyz"
  force_destroy = true 
}

resource "aws_s3_bucket_public_access_block" "silver_lake_block" {
  bucket = aws_s3_bucket.silver_lake.id

  block_public_acls       = true
  block_public_policy     = true
  ignore_public_acls      = true
  restrict_public_buckets = true
}

# S3 Event Notification: When Bronze gets a file, awake the Silver Lambda
resource "aws_s3_bucket_notification" "bronze_trigger_silver" {
  bucket = aws_s3_bucket.bronze_lake.id

  lambda_function {
    lambda_function_arn = aws_lambda_function.etl_github_silver_enrichment.arn
    events              = ["s3:ObjectCreated:*"]
    filter_prefix       = "github_events/"
  }

  depends_on = [aws_lambda_permission.allow_s3_to_call_silver]
}
