# Step 1: Terraform zips the source code
data "archive_file" "lambda_zip" {
  type        = "zip"
  source_dir  = "${path.module}/../src"
  output_path = "${path.module}/lambda.zip"
}

# Step 2: Terraform zips the installed dependencies (Layer)
data "archive_file" "lambda_layer_zip" {
  type        = "zip"
  source_dir  = "${path.module}/../layer"
  output_path = "${path.module}/layer.zip"
}

resource "aws_lambda_layer_version" "python_requirements_layer" {
  filename            = data.archive_file.lambda_layer_zip.output_path
  layer_name          = "etl_bronze_requirements"
  compatible_runtimes = ["python3.12"]
  source_code_hash    = data.archive_file.lambda_layer_zip.output_base64sha256
}

# Step 3: Main function creation
resource "aws_lambda_function" "etl_github_bronze" {
  filename         = data.archive_file.lambda_zip.output_path
  function_name    = "etl_github_events_extractor"
  role             = aws_iam_role.etl_lambda_role.arn
  handler          = "lambda_function.lambda_handler"
  runtime          = "python3.12"
  timeout          = 45  # Extended timeout for network latency
  memory_size      = 128 # Minimum required size for cost-effectiveness
  
  # Attach dependencies (layers)
  layers           = [aws_lambda_layer_version.python_requirements_layer.arn]
  source_code_hash = data.archive_file.lambda_zip.output_base64sha256

  # SQS binding for error handling
  dead_letter_config {
    target_arn = aws_sqs_queue.etl_bronze_dlq.arn
  }
}

# Step 4: EventBridge Trigger (Equivalent to Airflow Schedule)
resource "aws_cloudwatch_event_rule" "schedule_6_horas" {
  name                = "every_6_hours_1am_brt"
  description         = "Triggers at 1am BRT and in 6h intervals (UTC cron)"
  # 1am BRT is 4am UTC (4, 10, 16, 22)
  schedule_expression = "cron(0 4,10,16,22 * * ? *)" 
}

resource "aws_cloudwatch_event_target" "trigger_lambda" {
  rule      = aws_cloudwatch_event_rule.schedule_6_horas.name
  target_id = "etl_github_bronze"
  arn       = aws_lambda_function.etl_github_bronze.arn
}

resource "aws_lambda_permission" "allow_eventbridge_to_call_lambda" {
  statement_id  = "AllowExecutionFromEventBridge"
  action        = "lambda:InvokeFunction"
  function_name = aws_lambda_function.etl_github_bronze.function_name
  principal     = "events.amazonaws.com"
  source_arn    = aws_cloudwatch_event_rule.schedule_6_horas.arn
}


# ---------------------------------------------
# SILVER LAYER LAMBDA SETUP
# ---------------------------------------------

resource "aws_lambda_function" "etl_github_silver_enrichment" {
  filename         = data.archive_file.lambda_zip.output_path
  function_name    = "etl_github_events_silver_enricher"
  role             = aws_iam_role.etl_silver_lambda_role.arn
  handler          = "silver_lambda_function.lambda_handler"
  runtime          = "python3.12"
  timeout          = 300  # 5 minutes, allowing for HTTP fetch delays to avoid GitHub Rate Limiting
  memory_size      = 256  # Extra RAM for dictionary cache
  
  # RE-USE existing Pydantic + Requests layer! Cost optimized.
  layers           = [aws_lambda_layer_version.python_requirements_layer.arn]
  source_code_hash = data.archive_file.lambda_zip.output_base64sha256
}

# Permission to let the Bronze bucket trigger the Silver function
resource "aws_lambda_permission" "allow_s3_to_call_silver" {
  statement_id  = "AllowExecutionFromS3Bucket"
  action        = "lambda:InvokeFunction"
  function_name = aws_lambda_function.etl_github_silver_enrichment.arn
  principal     = "s3.amazonaws.com"
  source_arn    = aws_s3_bucket.bronze_lake.arn
}
