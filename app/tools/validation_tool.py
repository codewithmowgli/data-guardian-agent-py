import json
import logging
from langchain_core.tools import tool

logger = logging.getLogger(__name__)


@tool
def validate_payload(source_system: str, entity_type: str, payload_json: str) -> str:
    """Validate incoming payload against Salesforce schema and Lucid business rules. Returns validation result with errors."""
    logger.info(f"[VALIDATION-TOOL] Validating: source={source_system}, entity={entity_type}")

    errors = []
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

    valid = len(errors) == 0
    logger.info(f"[VALIDATION-TOOL] Result: valid={valid}, errors={len(errors)}, warnings={len(warnings)}")

    return json.dumps({"valid": valid, "errors": errors, "warnings": warnings})


@tool
def detect_conflicts(current_sf_record_json: str, incoming_payload_json: str) -> str:
    """Detect field-level conflicts between incoming data and the current Salesforce record. Returns a conflict report."""
    logger.info("[VALIDATION-TOOL] Detecting conflicts between incoming payload and SF record")

    conflicts = []
    severity = "NONE"

    try:
        current = json.loads(current_sf_record_json)
        incoming = json.loads(incoming_payload_json)

        if not current.get("found", False):
            return json.dumps({
                "hasConflicts": False,
                "conflicts": [],
                "severity": "NONE",
                "note": "No existing SF record — clean insert"
            })

        # Price conflict
        if "price" in current and "price" in incoming:
            diff = abs(float(current["price"]) - float(incoming["price"]))
            if diff > 0:
                conflicts.append(f"PRICE_MISMATCH: SF=${current['price']} vs incoming=${incoming['price']} (diff=${diff:.2f})")
                severity = "CRITICAL" if diff > 1000 else "HIGH" if diff > 100 else "MEDIUM"

        # Status conflict
        if "status" in current and "status" in incoming:
            if current["status"].lower() != incoming["status"].lower():
                conflicts.append(f"STATUS_CONFLICT: SF={current['status']} vs incoming={incoming['status']}")
                if current["status"] == "Active" and incoming["status"] == "Cancelled":
                    severity = "CRITICAL"
                elif severity == "NONE":
                    severity = "MEDIUM"

        # Stale update detection
        if "lastModifiedAt" in current and "timestamp" in incoming:
            if incoming["timestamp"] < current["lastModifiedAt"]:
                conflicts.append(f"STALE_UPDATE: Incoming timestamp {incoming['timestamp']} is older than SF record {current['lastModifiedAt']}")
                if severity == "NONE":
                    severity = "LOW"

        # Duplicate lead detection
        if "email" in current and "email" in incoming:
            if current["email"].lower() == incoming["email"].lower() and current.get("found"):
                conflicts.append(f"DUPLICATE_DETECTED: Lead with email {current['email']} already exists in Salesforce")
                if severity == "NONE":
                    severity = "HIGH"

    except json.JSONDecodeError as e:
        conflicts.append(f"Error during conflict detection: {str(e)}")
        severity = "HIGH"

    has_conflicts = len(conflicts) > 0
    logger.info(f"[VALIDATION-TOOL] Conflicts found: {len(conflicts)}, severity: {severity}")

    return json.dumps({
        "hasConflicts": has_conflicts,
        "conflictCount": len(conflicts),
        "severity": severity,
        "conflicts": conflicts
    })


# ── Entity Validators ────────────────────────────────────────────────────────

def _validate_lead(payload: dict, errors: list, warnings: list):
    if not payload.get("email") and not payload.get("phone"):
        errors.append("Lead must have at least email or phone")
    if not payload.get("firstName") or not payload.get("lastName"):
        errors.append("Lead must have firstName and lastName")
    if not payload.get("vehicleInterest"):
        warnings.append("Lead missing vehicleInterest — will affect lead scoring")


def _validate_order(payload: dict, errors: list, warnings: list):
    if not payload.get("customerId"):
        errors.append("Order missing required field: customerId")
    if not payload.get("vehicleModel"):
        errors.append("Order missing required field: vehicleModel")
    if not payload.get("price"):
        errors.append("Order missing required field: price")
    elif float(payload.get("price", 0)) <= 0:
        errors.append("Order price must be greater than 0")


def _validate_invoice(payload: dict, errors: list, warnings: list):
    if not payload.get("orderId"):
        errors.append("Invoice missing required field: orderId")
    if not payload.get("amount"):
        errors.append("Invoice missing required field: amount")
    if not payload.get("currency"):
        errors.append("Invoice missing required field: currency")


def _validate_subscription(payload: dict, errors: list, warnings: list):
    if not payload.get("customerId"):
        errors.append("Subscription missing required field: customerId")
    if not payload.get("plan"):
        errors.append("Subscription missing required field: plan")
    if not payload.get("status"):
        errors.append("Subscription missing required field: status")


def _validate_vehicle_config(payload: dict, errors: list, warnings: list):
    if not payload.get("model"):
        errors.append("VehicleConfig missing required field: model")
    if not payload.get("basePrice"):
        errors.append("VehicleConfig missing required field: basePrice")
    if not payload.get("configSessionId"):
        warnings.append("Missing configSessionId — cannot detect stale session")
