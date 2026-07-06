terraform {
  required_version = ">= 1.5.0"
  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = ">= 5.40.0"
    }
    archive = {
      source  = "hashicorp/archive"
      version = ">= 2.4.0"
    }
  }
}

provider "aws" {
  region = var.aws_region
}

locals {
  prefix = "${var.agent_name}-${var.environment}"
}

data "aws_caller_identity" "current" {}

# ═══════════════════════════════════════════════════════════════
# DynamoDB — Audit Log Table
# ═══════════════════════════════════════════════════════════════

resource "aws_dynamodb_table" "audit_log" {
  name         = "${local.prefix}-audit-log"
  billing_mode = "PAY_PER_REQUEST"
  hash_key     = "auditId"

  attribute {
    name = "auditId"
    type = "S"
  }

  ttl {
    attribute_name = "expiresAt"
    enabled        = true
  }

  tags = { Environment = var.environment, Project = "data-guardian-agent" }
}

# ═══════════════════════════════════════════════════════════════
# SNS — Slack & Jira notification topics
# ═══════════════════════════════════════════════════════════════

resource "aws_sns_topic" "slack_notifications" {
  name = "${local.prefix}-slack-notifications"
  tags = { Environment = var.environment, Project = "data-guardian-agent" }
}

resource "aws_sns_topic" "jira_escalations" {
  name = "${local.prefix}-jira-escalations"
  tags = { Environment = var.environment, Project = "data-guardian-agent" }
}

# ═══════════════════════════════════════════════════════════════
# IAM — Bedrock Agent Role
# ═══════════════════════════════════════════════════════════════

resource "aws_iam_role" "bedrock_agent_role" {
  name = "${local.prefix}-bedrock-agent-role"

  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Sid    = "BedrockAgentAssumeRole"
      Effect = "Allow"
      Principal = { Service = "bedrock.amazonaws.com" }
      Action    = "sts:AssumeRole"
      Condition = {
        StringEquals = {
          "aws:SourceAccount" = data.aws_caller_identity.current.account_id
        }
      }
    }]
  })
}

resource "aws_iam_role_policy" "bedrock_agent_policy" {
  name = "${local.prefix}-bedrock-agent-policy"
  role = aws_iam_role.bedrock_agent_role.id

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Sid    = "InvokeFoundationModel"
        Effect = "Allow"
        Action = ["bedrock:InvokeModel", "bedrock:InvokeModelWithResponseStream"]
        Resource = "arn:aws:bedrock:${var.aws_region}::foundation-model/${var.foundation_model}"
      },
      {
        Sid    = "InvokeLambdaTools"
        Effect = "Allow"
        Action = ["lambda:InvokeFunction"]
        Resource = [
          aws_lambda_function.salesforce.arn,
          aws_lambda_function.validation.arn,
          aws_lambda_function.audit.arn,
          aws_lambda_function.notification.arn,
        ]
      }
    ]
  })
}

# ═══════════════════════════════════════════════════════════════
# IAM — Lambda Role
# ═══════════════════════════════════════════════════════════════

resource "aws_iam_role" "lambda_role" {
  name = "${local.prefix}-lambda-role"

  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Effect    = "Allow"
      Principal = { Service = "lambda.amazonaws.com" }
      Action    = "sts:AssumeRole"
    }]
  })
}

resource "aws_iam_role_policy_attachment" "lambda_basic" {
  role       = aws_iam_role.lambda_role.name
  policy_arn = "arn:aws:iam::aws:policy/service-role/AWSLambdaBasicExecutionRole"
}

resource "aws_iam_role_policy" "lambda_data_policy" {
  name = "${local.prefix}-lambda-data-policy"
  role = aws_iam_role.lambda_role.id

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Sid      = "DynamoDBAuditLog"
        Effect   = "Allow"
        Action   = ["dynamodb:PutItem", "dynamodb:GetItem", "dynamodb:Query"]
        Resource = aws_dynamodb_table.audit_log.arn
      },
      {
        Sid      = "SNSPublish"
        Effect   = "Allow"
        Action   = ["sns:Publish"]
        Resource = [aws_sns_topic.slack_notifications.arn, aws_sns_topic.jira_escalations.arn]
      }
    ]
  })
}

# ═══════════════════════════════════════════════════════════════
# Lambda — Package each tool handler
# ═══════════════════════════════════════════════════════════════

data "archive_file" "salesforce_zip" {
  type        = "zip"
  source_file = "${path.module}/../lambda/salesforce/handler.py"
  output_path = "${path.module}/dist/salesforce.zip"
}

data "archive_file" "validation_zip" {
  type        = "zip"
  source_file = "${path.module}/../lambda/validation/handler.py"
  output_path = "${path.module}/dist/validation.zip"
}

data "archive_file" "audit_zip" {
  type        = "zip"
  source_file = "${path.module}/../lambda/audit/handler.py"
  output_path = "${path.module}/dist/audit.zip"
}

data "archive_file" "notification_zip" {
  type        = "zip"
  source_file = "${path.module}/../lambda/notification/handler.py"
  output_path = "${path.module}/dist/notification.zip"
}

resource "aws_lambda_function" "salesforce" {
  function_name    = "${local.prefix}-salesforce"
  role             = aws_iam_role.lambda_role.arn
  runtime          = var.lambda_runtime
  handler          = "handler.handler"
  filename         = data.archive_file.salesforce_zip.output_path
  source_code_hash = data.archive_file.salesforce_zip.output_base64sha256
  timeout          = var.lambda_timeout
  tags             = { Environment = var.environment, Project = "data-guardian-agent" }
}

resource "aws_lambda_function" "validation" {
  function_name    = "${local.prefix}-validation"
  role             = aws_iam_role.lambda_role.arn
  runtime          = var.lambda_runtime
  handler          = "handler.handler"
  filename         = data.archive_file.validation_zip.output_path
  source_code_hash = data.archive_file.validation_zip.output_base64sha256
  timeout          = var.lambda_timeout
  tags             = { Environment = var.environment, Project = "data-guardian-agent" }
}

resource "aws_lambda_function" "audit" {
  function_name    = "${local.prefix}-audit"
  role             = aws_iam_role.lambda_role.arn
  runtime          = var.lambda_runtime
  handler          = "handler.handler"
  filename         = data.archive_file.audit_zip.output_path
  source_code_hash = data.archive_file.audit_zip.output_base64sha256
  timeout          = var.lambda_timeout

  environment {
    variables = {
      AUDIT_TABLE = aws_dynamodb_table.audit_log.name
    }
  }
  tags = { Environment = var.environment, Project = "data-guardian-agent" }
}

resource "aws_lambda_function" "notification" {
  function_name    = "${local.prefix}-notification"
  role             = aws_iam_role.lambda_role.arn
  runtime          = var.lambda_runtime
  handler          = "handler.handler"
  filename         = data.archive_file.notification_zip.output_path
  source_code_hash = data.archive_file.notification_zip.output_base64sha256
  timeout          = var.lambda_timeout

  environment {
    variables = {
      SLACK_SNS_TOPIC_ARN = aws_sns_topic.slack_notifications.arn
      JIRA_SNS_TOPIC_ARN  = aws_sns_topic.jira_escalations.arn
    }
  }
  tags = { Environment = var.environment, Project = "data-guardian-agent" }
}

# Allow Bedrock to invoke all Lambdas
resource "aws_lambda_permission" "salesforce_bedrock" {
  statement_id  = "AllowBedrockInvoke"
  action        = "lambda:InvokeFunction"
  function_name = aws_lambda_function.salesforce.function_name
  principal     = "bedrock.amazonaws.com"
  source_arn    = "arn:aws:bedrock:${var.aws_region}:${data.aws_caller_identity.current.account_id}:agent/*"
}

resource "aws_lambda_permission" "validation_bedrock" {
  statement_id  = "AllowBedrockInvoke"
  action        = "lambda:InvokeFunction"
  function_name = aws_lambda_function.validation.function_name
  principal     = "bedrock.amazonaws.com"
  source_arn    = "arn:aws:bedrock:${var.aws_region}:${data.aws_caller_identity.current.account_id}:agent/*"
}

resource "aws_lambda_permission" "audit_bedrock" {
  statement_id  = "AllowBedrockInvoke"
  action        = "lambda:InvokeFunction"
  function_name = aws_lambda_function.audit.function_name
  principal     = "bedrock.amazonaws.com"
  source_arn    = "arn:aws:bedrock:${var.aws_region}:${data.aws_caller_identity.current.account_id}:agent/*"
}

resource "aws_lambda_permission" "notification_bedrock" {
  statement_id  = "AllowBedrockInvoke"
  action        = "lambda:InvokeFunction"
  function_name = aws_lambda_function.notification.function_name
  principal     = "bedrock.amazonaws.com"
  source_arn    = "arn:aws:bedrock:${var.aws_region}:${data.aws_caller_identity.current.account_id}:agent/*"
}

# ═══════════════════════════════════════════════════════════════
# S3 — OpenAPI schema for action group
# ═══════════════════════════════════════════════════════════════

resource "aws_s3_bucket" "agent_schemas" {
  bucket        = "${local.prefix}-schemas-${data.aws_caller_identity.current.account_id}"
  force_destroy = true
  tags          = { Environment = var.environment, Project = "data-guardian-agent" }
}

resource "aws_s3_bucket_versioning" "agent_schemas" {
  bucket = aws_s3_bucket.agent_schemas.id
  versioning_configuration { status = "Enabled" }
}

resource "aws_s3_object" "guardian_tools_schema" {
  bucket       = aws_s3_bucket.agent_schemas.id
  key          = "guardian_tools_schema.json"
  source       = "${path.module}/../schemas/guardian_tools_schema.json"
  content_type = "application/json"
  etag         = filemd5("${path.module}/../schemas/guardian_tools_schema.json")
}

# ═══════════════════════════════════════════════════════════════
# Bedrock AgentCore — Agent
# ═══════════════════════════════════════════════════════════════

resource "aws_bedrockagent_agent" "data_guardian_agent" {
  agent_name              = local.prefix
  agent_resource_role_arn = aws_iam_role.bedrock_agent_role.arn
  foundation_model        = var.foundation_model
  idle_session_ttl_in_seconds = 600

  instruction = <<-EOT
    You are the Lucid Data Guardian Agent — an autonomous AI system that ensures data integrity
    across Lucid Motors' enterprise systems and Salesforce as the system of record.

    You process incoming data events from 5 source systems:
    PARTNER_PORTAL, LUCID_COM, SUBSCRIPTION_APP, LUCID_FINANCE, SAP

    Follow this 7-step pipeline for every event:
    1. INGEST          — extract event_id, source_system, entity_type, entity_id, action, payload
    2. VALIDATE        — call validate_payload to check schema and business rules
    3. FETCH_SF        — call fetch_salesforce_record to get current Salesforce state
    4. CONFLICT_CHECK  — call detect_conflicts to compare incoming vs SF record
    5. DECISION        — based on validation + conflicts, decide:
       - APPROVE          : valid payload, no conflicts or resolvable minor conflicts
       - REJECT           : invalid payload (missing required fields, schema violation)
       - QUARANTINE       : valid payload but critical conflicts requiring human review
       - ESCALATE_TO_HUMAN: data integrity risk or unresolvable business rule violation
    6. ACTION          — execute decision:
       - APPROVE → call sync_to_salesforce
       - REJECT → call send_notification (channel: data-alerts, severity: HIGH)
       - QUARANTINE → call quarantine_record, then send_notification
       - ESCALATE_TO_HUMAN → call escalate_to_human
    7. AUDIT           — always call create_audit_entry with decision and reasoning

    Always respond with valid JSON:
    {
      "eventId": "...",
      "decision": "APPROVE | REJECT | QUARANTINE | ESCALATE_TO_HUMAN",
      "reasoning": "...",
      "sfRecordId": "... (if APPROVE)",
      "conflictSummary": "... (if conflicts found)"
    }

    Be deterministic. Every event must have a complete audit trail.
  EOT

  tags = { Environment = var.environment, Project = "data-guardian-agent" }
}

# ═══════════════════════════════════════════════════════════════
# Bedrock AgentCore — Action Groups (one per tool category)
# ═══════════════════════════════════════════════════════════════

resource "aws_bedrockagent_agent_action_group" "salesforce_tools" {
  agent_id          = aws_bedrockagent_agent.data_guardian_agent.id
  agent_version     = "DRAFT"
  action_group_name = "SalesforceTools"
  description       = "Fetch and sync records with Salesforce"

  action_group_executor {
    lambda = aws_lambda_function.salesforce.arn
  }

  api_schema {
    s3 {
      s3_bucket_name = aws_s3_bucket.agent_schemas.id
      s3_object_key  = aws_s3_object.guardian_tools_schema.key
    }
  }
}

resource "aws_bedrockagent_agent_action_group" "validation_tools" {
  agent_id          = aws_bedrockagent_agent.data_guardian_agent.id
  agent_version     = "DRAFT"
  action_group_name = "ValidationTools"
  description       = "Validate payloads and detect conflicts"

  action_group_executor {
    lambda = aws_lambda_function.validation.arn
  }

  api_schema {
    s3 {
      s3_bucket_name = aws_s3_bucket.agent_schemas.id
      s3_object_key  = aws_s3_object.guardian_tools_schema.key
    }
  }
}

resource "aws_bedrockagent_agent_action_group" "audit_tools" {
  agent_id          = aws_bedrockagent_agent.data_guardian_agent.id
  agent_version     = "DRAFT"
  action_group_name = "AuditTools"
  description       = "Create audit entries and quarantine records in DynamoDB"

  action_group_executor {
    lambda = aws_lambda_function.audit.arn
  }

  api_schema {
    s3 {
      s3_bucket_name = aws_s3_bucket.agent_schemas.id
      s3_object_key  = aws_s3_object.guardian_tools_schema.key
    }
  }
}

resource "aws_bedrockagent_agent_action_group" "notification_tools" {
  agent_id          = aws_bedrockagent_agent.data_guardian_agent.id
  agent_version     = "DRAFT"
  action_group_name = "NotificationTools"
  description       = "Send Slack notifications and Jira escalations via SNS"

  action_group_executor {
    lambda = aws_lambda_function.notification.arn
  }

  api_schema {
    s3 {
      s3_bucket_name = aws_s3_bucket.agent_schemas.id
      s3_object_key  = aws_s3_object.guardian_tools_schema.key
    }
  }
}

# ═══════════════════════════════════════════════════════════════
# Bedrock AgentCore — Agent Alias
# ═══════════════════════════════════════════════════════════════

resource "aws_bedrockagent_agent_alias" "data_guardian_alias" {
  agent_id         = aws_bedrockagent_agent.data_guardian_agent.id
  agent_alias_name = var.environment
  tags             = { Environment = var.environment, Project = "data-guardian-agent" }
}
