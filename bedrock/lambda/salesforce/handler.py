"""
Lambda handler for Data Guardian Agent — Salesforce Action Group.
Handles: fetch_salesforce_record, sync_to_salesforce
Invoked by AWS Bedrock AgentCore when the agent calls either Salesforce function.
"""
import json
import time


def handler(event, context):
    function_name = event.get("function", "")

    if function_name == "fetch_salesforce_record":
        return _fetch_record(event)
    elif function_name == "sync_to_salesforce":
        return _sync_record(event)
    else:
        return _response(event, json.dumps({"error": f"Unknown function: {function_name}"}))


# ── fetch_salesforce_record ───────────────────────────────────────────────────

def _fetch_record(event: dict) -> dict:
    object_type = _get_param(event, "object_type").upper()
    entity_id   = _get_param(event, "entity_id")

    match object_type:
        case "LEAD":
            body = _mock_lead(entity_id)
        case "ORDER":
            body = _mock_order(entity_id)
        case "INVOICE":
            body = _mock_invoice(entity_id)
        case "SUBSCRIPTION":
            body = _mock_subscription(entity_id)
        case "VEHICLE_CONFIG":
            body = _mock_vehicle_config(entity_id)
        case _:
            body = json.dumps({"found": False, "message": f"No record found for {object_type}/{entity_id}"})

    return _response(event, body)


def _mock_lead(entity_id: str) -> str:
    if "NEW" in entity_id:
        return json.dumps({"found": False, "message": "No existing lead found"})
    return json.dumps({
        "found": True, "sfRecordId": "LEAD-SF-001",
        "email": "customer@example.com", "firstName": "John", "lastName": "Smith",
        "vehicleInterest": "Lucid Air Grand Touring", "status": "Open",
        "createdAt": "2025-06-01T10:00:00Z", "lastModifiedAt": "2025-06-15T14:30:00Z"
    })


def _mock_order(entity_id: str) -> str:
    return json.dumps({
        "found": True, "sfRecordId": "ORDER-SF-001", "orderId": entity_id,
        "vehicleModel": "Lucid Air Pure", "price": 69900, "currency": "USD",
        "status": "Confirmed", "customerId": "CUST-001",
        "createdAt": "2025-05-20T09:00:00Z", "lastModifiedAt": "2025-06-10T11:00:00Z"
    })


def _mock_invoice(entity_id: str) -> str:
    return json.dumps({
        "found": True, "sfRecordId": "INV-SF-001", "invoiceId": entity_id,
        "orderId": "ORDER-001", "amount": 69900, "currency": "USD",
        "status": "Pending", "createdAt": "2025-06-05T08:00:00Z"
    })


def _mock_subscription(entity_id: str) -> str:
    return json.dumps({
        "found": True, "sfRecordId": "SUB-SF-001", "subscriptionId": entity_id,
        "customerId": "CUST-002", "plan": "Lucid Care Plus", "status": "Active",
        "renewalDate": "2026-01-01", "lastModifiedAt": "2025-06-01T10:00:00Z"
    })


def _mock_vehicle_config(entity_id: str) -> str:
    return json.dumps({
        "found": True, "sfRecordId": "CONFIG-SF-001", "configId": entity_id,
        "model": "Lucid Air Grand Touring", "basePrice": 138000,
        "color": "Stellar White", "lastModifiedAt": "2025-06-20T08:00:00Z"
    })


# ── sync_to_salesforce ────────────────────────────────────────────────────────

def _sync_record(event: dict) -> dict:
    object_type = _get_param(event, "object_type").upper()
    entity_id   = _get_param(event, "entity_id")
    sf_record_id = f"SF-{object_type[:3]}-{int(time.time())}"
    result = json.dumps({
        "success": True,
        "sfRecordId": sf_record_id,
        "message": f"Record {entity_id} upserted successfully into Salesforce {object_type}"
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
            "actionGroup":      event.get("actionGroup", "SalesforceTools"),
            "function":         event.get("function",    "fetch_salesforce_record"),
            "functionResponse": {
                "responseBody": {"TEXT": {"body": body}}
            }
        }
    }
