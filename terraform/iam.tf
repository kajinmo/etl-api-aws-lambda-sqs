data "aws_caller_identity" "current" {}
data "aws_region" "current" {}

# Trust Policy: Only AWS Lambda can assume this role
data "aws_iam_policy_document" "lambda_trust" {
  statement {
    actions = ["sts:AssumeRole"]
    principals {
      type        = "Service"
      identifiers = ["lambda.amazonaws.com"]
    }
  }
}

resource "aws_iam_role" "etl_lambda_role" {
  name               = "etl-bronze-lambda-role"
  assume_role_policy = data.aws_iam_policy_document.lambda_trust.json
}

# Strict Least Privilege Policy based on required scope
data "aws_iam_policy_document" "etl_lambda_policy_doc" {
  
  # Default CloudWatch access for Python logging
  statement {
    sid       = "AllowCloudWatchLogs"
    actions   = ["logs:CreateLogGroup", "logs:CreateLogStream", "logs:PutLogEvents"]
    resources = ["arn:aws:logs:${data.aws_region.current.name}:${data.aws_caller_identity.current.account_id}:log-group:/aws/lambda/*"]
  }

  # READ only the specific token from SSM Parameter Store (No wildcards '*')
  statement {
    sid       = "AllowSSMParameterRead"
    actions   = ["ssm:GetParameter"]
    resources = ["arn:aws:ssm:${data.aws_region.current.name}:${data.aws_caller_identity.current.account_id}:parameter/etl_github_token"]
  }

  # WRITE only to the S3 Bronze partition
  statement {
    sid       = "AllowS3BronzeWrite"
    actions   = ["s3:PutObject"]
    resources = ["${aws_s3_bucket.bronze_lake.arn}/github_events/*"]
  }

  # SEND errors to the SQS Dead Letter Queue
  statement {
    sid       = "AllowSQSDeadLetterQueue"
    actions   = ["sqs:SendMessage"]
    resources = [aws_sqs_queue.etl_bronze_dlq.arn]
  }
}

resource "aws_iam_role_policy" "etl_lambda_inline_policy" {
  name   = "etl-least-privilege-policy"
  role   = aws_iam_role.etl_lambda_role.id
  policy = data.aws_iam_policy_document.etl_lambda_policy_doc.json
}

# ---------------------------------------------
# SILVER LAYER IAM
# ---------------------------------------------

# Isolated Silver Execution Role
resource "aws_iam_role" "etl_silver_lambda_role" {
  name               = "etl-silver-lambda-role"
  assume_role_policy = data.aws_iam_policy_document.lambda_trust.json
}

data "aws_iam_policy_document" "etl_silver_policy_doc" {
  
  statement {
    sid       = "AllowCloudWatchLogs"
    actions   = ["logs:CreateLogGroup", "logs:CreateLogStream", "logs:PutLogEvents"]
    resources = ["arn:aws:logs:${data.aws_region.current.name}:${data.aws_caller_identity.current.account_id}:log-group:/aws/lambda/*"]
  }

  statement {
    sid       = "AllowSSMParameterRead"
    actions   = ["ssm:GetParameter"]
    resources = ["arn:aws:ssm:${data.aws_region.current.name}:${data.aws_caller_identity.current.account_id}:parameter/etl_github_token"]
  }

  # SILVER MUST READ BRONZE
  statement {
    sid       = "AllowS3BronzeRead"
    actions   = ["s3:GetObject"]
    resources = ["${aws_s3_bucket.bronze_lake.arn}/github_events/*"]
  }

  # SILVER MUST WRITE SILVER ONLY
  statement {
    sid       = "AllowS3SilverWrite"
    actions   = ["s3:PutObject"]
    resources = ["${aws_s3_bucket.silver_lake.arn}/github_events/*"]
  }
}

resource "aws_iam_role_policy" "etl_silver_inline_policy" {
  name   = "etl-silver-least-privilege-policy"
  role   = aws_iam_role.etl_silver_lambda_role.id
  policy = data.aws_iam_policy_document.etl_silver_policy_doc.json
}
