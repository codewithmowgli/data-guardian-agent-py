#!/bin/bash
# ─────────────────────────────────────────────────────────────────────────────
# deploy_bedrock.sh — Deploy Lucid Data Guardian Agent to AWS Bedrock AgentCore
#
# Prerequisites:
#   - AWS CLI configured: aws configure
#   - Terraform >= 1.5 installed
#   - Bedrock model access enabled in AWS Console:
#     Bedrock → Model access → anthropic.claude-3-5-sonnet-20241022-v2:0
#
# Usage:
#   ./scripts/deploy_bedrock.sh [dev|staging|prod]
# ─────────────────────────────────────────────────────────────────────────────

set -euo pipefail

ENVIRONMENT=${1:-dev}
TERRAFORM_DIR="$(dirname "$0")/../bedrock/terraform"

echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "  Lucid Data Guardian Agent — Bedrock AgentCore Deployment"
echo "  Environment: $ENVIRONMENT"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"

# ── Step 1: Verify AWS credentials ──────────────────────────────
echo ""
echo "[1/5] Verifying AWS credentials..."
aws sts get-caller-identity
echo "✓ AWS credentials valid"

# ── Step 2: Verify Bedrock model access ─────────────────────────
echo ""
echo "[2/5] Checking Bedrock model access..."
MODEL_ID="anthropic.claude-3-5-sonnet-20241022-v2:0"
aws bedrock get-foundation-model --model-identifier "$MODEL_ID" \
  --query 'modelDetails.modelName' --output text || {
    echo "✗ ERROR: Model access not enabled."
    echo "  Go to: AWS Console → Bedrock → Model access → Request access → Claude 3.5 Sonnet"
    exit 1
  }
echo "✓ Model access confirmed: $MODEL_ID"

# ── Step 3: Terraform init ───────────────────────────────────────
echo ""
echo "[3/5] Initializing Terraform..."
mkdir -p "$TERRAFORM_DIR/dist"
cd "$TERRAFORM_DIR"
terraform init -upgrade
echo "✓ Terraform initialized"

# ── Step 4: Terraform plan ───────────────────────────────────────
echo ""
echo "[4/5] Terraform plan..."
terraform plan \
  -var="environment=$ENVIRONMENT" \
  -out=tfplan
echo "✓ Plan complete — review above before applying"

# ── Step 5: Terraform apply ──────────────────────────────────────
echo ""
echo "[5/5] Applying infrastructure..."
terraform apply tfplan

echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "  ✓ Deployment complete!"
echo ""
echo "  Agent ID:        $(terraform output -raw agent_id)"
echo "  Agent Alias ID:  $(terraform output -raw agent_alias_id)"
echo "  Audit DynamoDB:  $(terraform output -raw audit_dynamodb_table)"
echo "  Slack SNS ARN:   $(terraform output -raw slack_sns_topic_arn)"
echo ""
echo "  To invoke the agent:"
terraform output -raw invoke_command
echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
