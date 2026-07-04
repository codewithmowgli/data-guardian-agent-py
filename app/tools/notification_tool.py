import logging
import time
from langchain_core.tools import tool

logger = logging.getLogger(__name__)


@tool
def send_notification(channel: str, severity: str, message: str) -> str:
    """Send a notification to the appropriate channel based on severity. Use for REJECT, QUARANTINE, and ESCALATE decisions."""
    icons = {"CRITICAL": "🚨", "HIGH": "⚠️", "WARNING": "⚠️"}
    icon = icons.get(severity.upper(), "ℹ️")
    log_message = f"{icon} [{severity}] #{channel}: {message}"
    logger.warning(f"[SLACK-MOCK] {log_message}")
    return f'{{"sent": true, "channel": "{channel}", "severity": "{severity}"}}'


@tool
def escalate_to_human(issue_title: str, description: str, assignee: str) -> str:
    """Escalate a critical data conflict to a human data steward via Jira ticket and Slack DM."""
    logger.error(f"[NOTIFICATION-TOOL] 🚨 ESCALATING TO HUMAN: {issue_title}")
    logger.error(f"[NOTIFICATION-TOOL] Assignee: {assignee}")
    logger.error(f"[NOTIFICATION-TOOL] Description: {description}")

    jira_ticket_id = f"DATA-{int(time.time()) % 10000}"
    logger.error(f"[JIRA-MOCK] Created ticket {jira_ticket_id} assigned to {assignee} — {issue_title}")

    return f"""{{
        "escalated": true,
        "jiraTicketId": "{jira_ticket_id}",
        "assignee": "{assignee}",
        "message": "Human escalation created. Data steward notified via Slack and Jira."
    }}"""
