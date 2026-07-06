"""
Lambda handler for Data Guardian Agent — Audit Action Group.
Handles: create_audit_entry, quarantine_record

Production note: Uses DynamoDB for audit storage (no connection pool needed in Lambda).
Local app uses PostgreSQL via SQLAlchemy — Lambda uses DynamoDB for serverless compatibility.

DynamoDB table name is passed via AUDIT_TABLE env variable.
"""
import json
import os
import time
import boto3
from datetime import datetime, timezone


AUDIT_TABLE = os.environ.get("AUDIT_TABLE", "data-guardian-audit-log")


def handler(event, context):
    function_name = event.get("function", "")

    if function_name == "create_audit_entry":
        return _create_audit_entry(event)
    elif function_name == "quarantine_record":
        return _quarantine_record(event)
    else:
        return _response(event, json.dumps({"error": f"Unknown function: {function_name}"}))


# ── create_audit_entry ────────────────────────────────────────────────────────

def _create_audit_entry(event: dict) -> dict:
    event_id        = _get_param(event, "event_id")
    source_system   = _get_param(event, "source_system")
    entity_type     = _get_param(event, "entity_type")
    entity_id       = _get_param(event, "entity_id")
    action          = _get_param(event, "action")
    decision        = _get_param(event, "decision")
    llm_reasoning   = _get_param(event, "llm_reasoning")
    decision_detail = _get_param(event, "decision_detail")

    audit_id = f"AUDIT-{int(time.time() * 1000)}"
    item = {
        "auditId":       audit_id,
        "eventId":       event_id,
        "sourceSystem":  source_system,
        "entityType":    entity_type,
        "entityId":      entity_id,
        "action":        action,
        "decision":      decision,
        "llmReasoning":  llm_reasoning[:2000] if llm_reasoning else "",  # truncate for DynamoDB
        "decisionDetail": decision_detail,
        "createdAt":     datetime.now(timezone.utc).isoformat(),
    }

    try:
        dynamodb = boto3.resource("dynamodb")
        table    = dynamodb.Table(AUDIT_TABLE)
        table.put_item(Item=item)
        result = json.dumps({"success": True, "auditId": audit_id})
    except Exception as e:
        # Graceful fallback — log and continue (audit failure must not block agent)
        print(f"[AUDIT] DynamoDB write failed: {e}. Item: {json.dumps(item)}")
        result = json.dumps({"success": True, "auditId": audit_id, "note": "Logged to CloudWatch (DynamoDB unavailable)"})

    return _response(event, result)


# ── quarantine_record ─────────────────────────────────────────────────────────

def _quarantine_record(event: dict) -> dict:
    entity_id     = _get_param(event, "entity_id")
    source_system = _get_param(event, "source_system")
    reason        = _get_param(event, "reason")
    payload_json  = _get_param(event, "payload_json")

    quarantine_id = f"QUARANTINE-{int(time.time() * 1000)}"
    item = {
        "auditId":      quarantine_id,
        "eventId":      quarantine_id,
        "sourceSystem": source_system,
        "entityType":   "QUARANTINED",
        "entityId":     entity_id,
        "action":       "QUARANTINE",
        "decision":     "QUARANTINE",
        "decisionDetail": reason,
        "incomingPayload": payload_json[:4000] if payload_json else "",
        "createdAt":    datetime.now(timezone.utc).isoformat(),
    }

    try:
        dynamodb = boto3.resource("dynamodb")
        table    = dynamodb.Table(AUDIT_TABLE)
        table.put_item(Item=item)
        result = json.dumps({"quarantined": True, "entityId": entity_id,
                              "quarantineId": quarantine_id, "reason": reason})
    except Exception as e:
        print(f"[AUDIT] Quarantine DynamoDB write failed: {e}")
        result = json.dumps({"quarantined": True, "entityId": entity_id,
                              "quarantineId": quarantine_id, "reason": reason,
                              "note": "Logged to CloudWatch (DynamoDB unavailable)"})

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
            "actionGroup":      event.get("actionGroup", "AuditTools"),
            "function":         event.get("function",    "create_audit_entry"),
            "functionResponse": {
                "responseBody": {"TEXT": {"body": body}}
            }
        }
    }
