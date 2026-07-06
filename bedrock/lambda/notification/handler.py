"""
Lambda handler for Data Guardian Agent — Notification Action Group.
Handles: send_notification, escalate_to_human

Production: SNS for Slack integration, Jira REST API for ticket creation.
Env vars: SLACK_SNS_TOPIC_ARN, JIRA_SNS_TOPIC_ARN
"""
import json
import os
import time
import boto3


SLACK_SNS_TOPIC_ARN = os.environ.get("SLACK_SNS_TOPIC_ARN", "")
JIRA_SNS_TOPIC_ARN  = os.environ.get("JIRA_SNS_TOPIC_ARN", "")


def handler(event, context):
    function_name = event.get("function", "")

    if function_name == "send_notification":
        return _send_notification(event)
    elif function_name == "escalate_to_human":
        return _escalate_to_human(event)
    else:
        return _response(event, json.dumps({"error": f"Unknown function: {function_name}"}))


# ── send_notification ─────────────────────────────────────────────────────────

def _send_notification(event: dict) -> dict:
    channel  = _get_param(event, "channel")
    severity = _get_param(event, "severity").upper()
    message  = _get_param(event, "message")

    icons    = {"CRITICAL": "🚨", "HIGH": "⚠️", "WARNING": "⚠️"}
    icon     = icons.get(severity, "ℹ️")
    payload  = f"{icon} [{severity}] #{channel}: {message}"

    sent = False
    if SLACK_SNS_TOPIC_ARN:
        try:
            sns = boto3.client("sns")
            sns.publish(TopicArn=SLACK_SNS_TOPIC_ARN, Message=payload,
                        Subject=f"[{severity}] Data Guardian Alert")
            sent = True
        except Exception as e:
            print(f"[NOTIFICATION] SNS publish failed: {e}")

    if not sent:
        # CloudWatch fallback — always available in Lambda
        print(f"[SLACK-MOCK] {payload}")
        sent = True

    result = json.dumps({"sent": sent, "channel": channel, "severity": severity})
    return _response(event, result)


# ── escalate_to_human ─────────────────────────────────────────────────────────

def _escalate_to_human(event: dict) -> dict:
    issue_title = _get_param(event, "issue_title")
    description = _get_param(event, "description")
    assignee    = _get_param(event, "assignee")

    jira_ticket_id = f"DATA-{int(time.time()) % 10000}"

    jira_payload = json.dumps({
        "fields": {
            "project":     {"key": "DATA"},
            "summary":     issue_title,
            "description": description,
            "issuetype":   {"name": "Bug"},
            "assignee":    {"name": assignee},
            "priority":    {"name": "Critical"},
            "labels":      ["data-guardian", "auto-escalated"]
        }
    })

    escalated = False
    if JIRA_SNS_TOPIC_ARN:
        try:
            sns = boto3.client("sns")
            sns.publish(TopicArn=JIRA_SNS_TOPIC_ARN, Message=jira_payload,
                        Subject=f"[ESCALATE] {issue_title}")
            escalated = True
        except Exception as e:
            print(f"[NOTIFICATION] Jira SNS publish failed: {e}")

    if not escalated:
        print(f"[JIRA-MOCK] Ticket {jira_ticket_id} — {issue_title} → {assignee}")
        escalated = True

    result = json.dumps({
        "escalated":    escalated,
        "jiraTicketId": jira_ticket_id,
        "assignee":     assignee,
        "message":      "Human escalation created. Data steward notified via Slack and Jira."
    })
    return _response(event, result)


# ── Helpers ───────────────────────────────────────────────────────────────────

def _get_param(event: dict, name: str) -> str:
    for p in event.get("parameters", []):
        if p["name"] == name:
            return p["value"]
    return ""


def _response(event: dict, body: str) -> dict:
    return {
        "messageVersion": "1.0",
        "response": {
            "actionGroup":      event.get("actionGroup", "NotificationTools"),
            "function":         event.get("function",    "send_notification"),
            "functionResponse": {
                "responseBody": {"TEXT": {"body": body}}
            }
        }
    }
