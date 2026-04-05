terraform {
  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 5.0"
    }
  }

  # --- Backend Remoto ---
  # Em um ambiente de produção, o estado do Terraform (.tfstate) nunca deve ficar local.
  # Recomenda-se o uso de um bucket S3 com versionamento e DynamoDB para State Locking.
  #
  # backend "s3" {
  #   bucket         = "<nome-do-bucket-tfstate>"
  #   key            = "bronze/<nome-do-projeto>/terraform.tfstate"
  #   region         = "<nome-da-regiao>"
  #   encrypt        = true
  #   dynamodb_table = "<nome-da-tabela-dynamodb>"
  # }
}

provider "aws" {
  region = "us-east-1"
  default_tags {
    tags = {
      Project     = "ETL-API-Lambda-SQS"
      Environment = "Bronze"
      ManagedBy   = "Terraform"
    }
  }
}
