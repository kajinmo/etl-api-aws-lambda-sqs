# Main queue for failed messages (DLQ - Dead Letter Queue)
resource "aws_sqs_queue" "etl_bronze_dlq" {
  name                      = "etl-bronze-dlq"
  message_retention_seconds = 1209600 # 14 Days (Maximum allowed) for troubleshooting
  
  # Free tier protection with AWS managed encryption
  sqs_managed_sse_enabled = true
}
