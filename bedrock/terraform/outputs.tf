output "agent_id" {
  description = "Bedrock AgentCore agent ID"
  value       = aws_bedrockagent_agent.data_guardian_agent.id
}

output "agent_alias_id" {
  description = "Bedrock AgentCore agent alias ID (use this to invoke)"
  value       = aws_bedrockagent_agent_alias.data_guardian_alias.agent_alias_id
}

output "agent_arn" {
  description = "Bedrock AgentCore agent ARN"
  value       = aws_bedrockagent_agent.data_guardian_agent.agent_arn
}

output "audit_dynamodb_table" {
  description = "DynamoDB table name for audit logs"
  value       = aws_dynamodb_table.audit_log.name
}

output "slack_sns_topic_arn" {
  description = "SNS topic ARN for Slack notifications"
  value       = aws_sns_topic.slack_notifications.arn
}

output "jira_sns_topic_arn" {
  description = "SNS topic ARN for Jira escalations"
  value       = aws_sns_topic.jira_escalations.arn
}

output "invoke_command" {
  description = "AWS CLI command to invoke the agent"
  value       = <<-EOT
    aws bedrock-agent-runtime invoke-agent \
      --agent-id ${aws_bedrockagent_agent.data_guardian_agent.id} \
      --agent-alias-id ${aws_bedrockagent_agent_alias.data_guardian_alias.agent_alias_id} \
      --session-id test-session-001 \
      --input-text '{"event_id":"EVT-001","source_system":"PARTNER_PORTAL","entity_type":"LEAD","entity_id":"LEAD-NEW-001","action":"UPSERT","payload_json":"{\"entityId\":\"LEAD-NEW-001\",\"email\":\"john@example.com\",\"firstName\":\"John\",\"lastName\":\"Smith\",\"vehicleInterest\":\"Lucid Air Grand Touring\",\"timestamp\":\"2025-06-01T10:00:00Z\"}"}' \
      outfile.txt
  EOT
}
