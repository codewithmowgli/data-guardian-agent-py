variable "aws_region" {
  description = "AWS region to deploy Bedrock AgentCore resources"
  type        = string
  default     = "us-east-1"
}

variable "environment" {
  description = "Deployment environment (dev, staging, prod)"
  type        = string
  default     = "dev"
}

variable "agent_name" {
  description = "Name of the Bedrock agent"
  type        = string
  default     = "lucid-data-guardian-agent"
}

variable "foundation_model" {
  description = "Bedrock foundation model ID"
  type        = string
  default     = "anthropic.claude-3-5-sonnet-20241022-v2:0"
}

variable "lambda_runtime" {
  description = "Lambda runtime"
  type        = string
  default     = "python3.12"
}

variable "lambda_timeout" {
  description = "Lambda timeout in seconds"
  type        = number
  default     = 30
}

variable "audit_dynamodb_table" {
  description = "DynamoDB table name for audit log storage"
  type        = string
  default     = "data-guardian-audit-log"
}
