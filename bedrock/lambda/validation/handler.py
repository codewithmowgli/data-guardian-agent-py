"""
Lambda handler for Data Guardian Agent — Validation Action Group.
Handles: validate_payload, detect_conflicts
Invoked by AWS Bedrock AgentCore when the agent calls either validation function.
"""
import json


def handler(event, context):
    function_name = event.get("function", "")

    if function_name == "validate_payload":
        return _validate_payload(event)
    elif function_name == "detect_conflicts":
        return _detect_conflicts(event)
    else:
        return _response(event, json.dumps({"error": f"Unknown function: {function_name}"}))


# ── validate_payload ──────────────────────────────────────────────────────────

def _validate_payload(event: dict) -> dict:
    source_system = _get_param(event, "source_system")
    entity_type   = _get_param(event, "entity_type")
    payload_json  = _get_param(event, "payload_json")

    errors   = []
    warnings = []

    try:
        payload = json.loads(payload_json)

        if not payload.get("entityId"):
            errors.append("Missing required field: entityId")
        if not payload.get("timestamp"):
            errors.append("Missing required field: timestamp")

        match entity_type.upper():
            case "LEAD":
                _validate_lead(payload, errors, warnings)
            case "ORDER":
                _validate_order(payload, errors, warnings)
            case "INVOICE":
                _validate_invoice(payload, errors, warnings)
            case "SUBSCRIPTION":
                _validate_subscription(payload, errors, warnings)
            case "VEHICLE_CONFIG":
                _validate_vehicle_config(payload, errors, warnings)
            case _:
                errors.append(f"Unknown entity type: {entity_type}")

        if source_system == "SAP" and entity_type.upper() == "ORDER":
            if not payload.get("currency"):
                errors.append("SAP orders must include currency code")

    except json.JSONDecodeError as e:
        errors.append(f"Invalid JSON payload: {str(e)}")

    result = json.dumps({"valid": len(errors) == 0, "errors": errors, "warnings": warnings})
    return _response(event, result)


def _validate_lead(payload, errors, warnings):
    if not payload.get("email") and not payload.get("phone"):
        errors.append("Lead must have at least email or phone")
    if not payload.get("firstName") or not payload.get("lastName"):
        errors.append("Lead must have firstName and lastName")
    if not payload.get("vehicleInterest"):
        warnings.append("Lead missing vehicleInterest — will affect lead scoring")


def _validate_order(payload, errors, warnings):
    if not payload.get("customerId"):
        errors.append("Order missing required field: customerId")
    if not payload.get("vehicleModel"):
        errors.append("Order missing required field: vehicleModel")
    if not payload.get("price") or float(payload.get("price", 0)) <= 0:
        errors.append("Order must have price > 0")


def _validate_invoice(payload, errors, warnings):
    if not payload.get("orderId"):
        errors.append("Invoice missing required field: orderId")
    if not payload.get("amount"):
        errors.append("Invoice missing required field: amount")
    if not payload.get("currency"):
        errors.append("Invoice missing required field: currency")


def _validate_subscription(payload, errors, warnings):
    if not payload.get("customerId"):
        errors.append("Subscription missing required field: customerId")
    if not payload.get("plan"):
        errors.append("Subscription missing required field: plan")
    if not payload.get("status"):
        errors.append("Subscription missing required field: status")


def _validate_vehicle_config(payload, errors, warnings):
    if not payload.get("model"):
        errors.append("VehicleConfig missing required field: model")
    if not payload.get("basePrice"):
        errors.append("VehicleConfig missing required field: basePrice")
    if not payload.get("configSessionId"):
        warnings.append("Missing configSessionId — cannot detect stale session")


# ── detect_conflicts ──────────────────────────────────────────────────────────

def _detect_conflicts(event: dict) -> dict:
    current_sf_json  = _get_param(event, "current_sf_record_json")
    incoming_json    = _get_param(event, "incoming_payload_json")

    conflicts = []
    severity  = "NONE"

    try:
        current  = json.loads(current_sf_json)
        incoming = json.loads(incoming_json)

        if not current.get("found", False):
            result = json.dumps({
                "hasConflicts": False, "conflicts": [],
                "severity": "NONE", "note": "No existing SF record — clean insert"
            })
            return _response(event, result)

        if "price" in current and "price" in incoming:
            diff = abs(float(current["price"]) - float(incoming["price"]))
            if diff > 0:
                conflicts.append(f"PRICE_MISMATCH: SF=${current['price']} vs incoming=${incoming['price']} (diff=${diff:.2f})")
                severity = "CRITICAL" if diff > 1000 else "HIGH" if diff > 100 else "MEDIUM"

        if "status" in current and "status" in incoming:
            if current["status"].lower() != incoming["status"].lower():
                conflicts.append(f"STATUS_CONFLICT: SF={current['status']} vs incoming={incoming['status']}")
                if current["status"] == "Active" and incoming["status"] == "Cancelled":
                    severity = "CRITICAL"
                elif severity == "NONE":
                    severity = "MEDIUM"

        if "lastModifiedAt" in current and "timestamp" in incoming:
            if incoming["timestamp"] < current["lastModifiedAt"]:
                conflicts.append(f"STALE_UPDATE: incoming {incoming['timestamp']} older than SF {current['lastModifiedAt']}")
                if severity == "NONE":
                    severity = "LOW"

        if "email" in current and "email" in incoming:
            if current["email"].lower() == incoming["email"].lower() and current.get("found"):
                conflicts.append(f"DUPLICATE_DETECTED: Lead with email {current['email']} already exists")
                if severity == "NONE":
                    severity = "HIGH"

    except json.JSONDecodeError as e:
        conflicts.append(f"Conflict detection error: {str(e)}")
        severity = "HIGH"

    result = json.dumps({
        "hasConflicts": len(conflicts) > 0,
        "conflictCount": len(conflicts),
        "severity": severity,
        "conflicts": conflicts
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
            "actionGroup":      event.get("actionGroup", "ValidationTools"),
            "function":         event.get("function",    "validate_payload"),
            "functionResponse": {
                "responseBody": {"TEXT": {"body": body}}
            }
        }
    }
