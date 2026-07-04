import logging
import time
from langchain_core.tools import tool

logger = logging.getLogger(__name__)


@tool
def fetch_salesforce_record(object_type: str, entity_id: str) -> str:
    """Fetch the current record from Salesforce by object type and entity ID. Returns current SF state as JSON."""
    logger.info(f"[SF-TOOL] Fetching SF record: type={object_type}, id={entity_id}")

    match object_type.upper():
        case "LEAD":
            return _mock_lead(entity_id)
        case "ORDER":
            return _mock_order(entity_id)
        case "INVOICE":
            return _mock_invoice(entity_id)
        case "SUBSCRIPTION":
            return _mock_subscription(entity_id)
        case "VEHICLE_CONFIG":
            return _mock_vehicle_config(entity_id)
        case _:
            return f'{{"found": false, "message": "No record found for {object_type}/{entity_id}"}}'


@tool
def sync_to_salesforce(object_type: str, entity_id: str, payload_json: str) -> str:
    """Sync an approved record to Salesforce via upsert. Returns the Salesforce record ID on success."""
    logger.info(f"[SF-TOOL] Syncing to Salesforce: type={object_type}, id={entity_id}")
    sf_record_id = f"SF-{object_type[:3].upper()}-{int(time.time())}"
    logger.info(f"[SF-TOOL] Successfully synced. SF Record ID: {sf_record_id}")
    return f'{{"success": true, "sfRecordId": "{sf_record_id}", "message": "Record upserted successfully"}}'


# ── Mock SF Records ──────────────────────────────────────────────────────────

def _mock_lead(entity_id: str) -> str:
    if "NEW" in entity_id:
        return '{"found": false, "message": "No existing lead found"}'
    return """{
        "found": true,
        "sfRecordId": "LEAD-SF-001",
        "email": "customer@example.com",
        "firstName": "John",
        "lastName": "Smith",
        "vehicleInterest": "Lucid Air Grand Touring",
        "status": "Open",
        "createdAt": "2025-06-01T10:00:00Z",
        "lastModifiedAt": "2025-06-15T14:30:00Z"
    }"""


def _mock_order(entity_id: str) -> str:
    return f"""{{
        "found": true,
        "sfRecordId": "ORDER-SF-001",
        "orderId": "{entity_id}",
        "vehicleModel": "Lucid Air Pure",
        "price": 69900,
        "currency": "USD",
        "status": "Confirmed",
        "customerId": "CUST-001",
        "createdAt": "2025-05-20T09:00:00Z",
        "lastModifiedAt": "2025-06-10T11:00:00Z"
    }}"""


def _mock_invoice(entity_id: str) -> str:
    return f"""{{
        "found": true,
        "sfRecordId": "INV-SF-001",
        "invoiceId": "{entity_id}",
        "orderId": "ORDER-001",
        "amount": 69900,
        "currency": "USD",
        "status": "Pending",
        "createdAt": "2025-06-05T08:00:00Z"
    }}"""


def _mock_subscription(entity_id: str) -> str:
    return f"""{{
        "found": true,
        "sfRecordId": "SUB-SF-001",
        "subscriptionId": "{entity_id}",
        "customerId": "CUST-002",
        "plan": "Lucid Care Plus",
        "status": "Active",
        "renewalDate": "2026-01-01",
        "lastModifiedAt": "2025-06-01T10:00:00Z"
    }}"""


def _mock_vehicle_config(entity_id: str) -> str:
    return f"""{{
        "found": true,
        "sfRecordId": "CONFIG-SF-001",
        "configId": "{entity_id}",
        "model": "Lucid Air Grand Touring",
        "basePrice": 138000,
        "color": "Stellar White",
        "lastPriceUpdate": "2025-06-20T00:00:00Z",
        "lastModifiedAt": "2025-06-20T08:00:00Z"
    }}"""
