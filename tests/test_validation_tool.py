import json
import pytest
from app.tools.validation_tool import validate_payload, detect_conflicts


def invoke(tool_func, **kwargs):
    """Helper to invoke LangChain tools directly in tests."""
    return tool_func.invoke(kwargs)


class TestValidatePayload:

    def test_valid_lead_passes(self):
        payload = json.dumps({
            "entityId": "LEAD-001",
            "timestamp": "2025-06-01T10:00:00Z",
            "email": "john@example.com",
            "firstName": "John",
            "lastName": "Smith",
            "vehicleInterest": "Lucid Air Grand Touring"
        })
        result = json.loads(invoke(validate_payload, source_system="PARTNER_PORTAL", entity_type="LEAD", payload_json=payload))
        assert result["valid"] is True
        assert result["errors"] == []

    def test_lead_missing_contact_fails(self):
        payload = json.dumps({
            "entityId": "LEAD-002",
            "timestamp": "2025-06-01T10:00:00Z",
            "firstName": "Jane",
            "lastName": "Doe"
        })
        result = json.loads(invoke(validate_payload, source_system="PARTNER_PORTAL", entity_type="LEAD", payload_json=payload))
        assert result["valid"] is False
        assert any("email or phone" in e for e in result["errors"])

    def test_valid_order_passes(self):
        payload = json.dumps({
            "entityId": "ORDER-001",
            "timestamp": "2025-06-01T10:00:00Z",
            "customerId": "CUST-001",
            "vehicleModel": "Lucid Air Pure",
            "price": 69900,
            "currency": "USD"
        })
        result = json.loads(invoke(validate_payload, source_system="PARTNER_PORTAL", entity_type="ORDER", payload_json=payload))
        assert result["valid"] is True

    def test_order_zero_price_fails(self):
        payload = json.dumps({
            "entityId": "ORDER-002",
            "timestamp": "2025-06-01T10:00:00Z",
            "customerId": "CUST-001",
            "vehicleModel": "Lucid Air Pure",
            "price": 0
        })
        result = json.loads(invoke(validate_payload, source_system="SAP", entity_type="ORDER", payload_json=payload))
        assert result["valid"] is False

    def test_invalid_json_fails(self):
        result = json.loads(invoke(validate_payload, source_system="SAP", entity_type="ORDER", payload_json="not-json"))
        assert result["valid"] is False
        assert any("Invalid JSON" in e for e in result["errors"])


class TestDetectConflicts:

    def test_no_conflict_on_new_record(self):
        sf = json.dumps({"found": False, "message": "No record found"})
        incoming = json.dumps({"entityId": "LEAD-NEW", "email": "new@example.com", "timestamp": "2025-06-01T10:00:00Z"})
        result = json.loads(invoke(detect_conflicts, current_sf_record_json=sf, incoming_payload_json=incoming))
        assert result["hasConflicts"] is False
        assert result["note"] == "No existing SF record — clean insert"

    def test_price_conflict_detected(self):
        sf = json.dumps({"found": True, "price": 92500, "status": "Confirmed", "lastModifiedAt": "2025-06-01T10:00:00Z"})
        incoming = json.dumps({"entityId": "ORDER-001", "price": 89900, "timestamp": "2025-06-02T10:00:00Z"})
        result = json.loads(invoke(detect_conflicts, current_sf_record_json=sf, incoming_payload_json=incoming))
        assert result["hasConflicts"] is True
        assert any("PRICE_MISMATCH" in c for c in result["conflicts"])

    def test_stale_update_detected(self):
        sf = json.dumps({"found": True, "status": "Active", "lastModifiedAt": "2025-06-20T10:00:00Z"})
        incoming = json.dumps({"entityId": "CONFIG-001", "timestamp": "2025-06-01T08:00:00Z"})
        result = json.loads(invoke(detect_conflicts, current_sf_record_json=sf, incoming_payload_json=incoming))
        assert any("STALE_UPDATE" in c for c in result["conflicts"])

    def test_duplicate_lead_detected(self):
        sf = json.dumps({"found": True, "email": "customer@example.com", "status": "Open", "lastModifiedAt": "2025-06-01T10:00:00Z"})
        incoming = json.dumps({"entityId": "LEAD-003", "email": "customer@example.com", "timestamp": "2025-06-02T10:00:00Z"})
        result = json.loads(invoke(detect_conflicts, current_sf_record_json=sf, incoming_payload_json=incoming))
        assert any("DUPLICATE_DETECTED" in c for c in result["conflicts"])

    def test_status_conflict_detected(self):
        sf = json.dumps({"found": True, "status": "Active", "lastModifiedAt": "2025-06-01T10:00:00Z"})
        incoming = json.dumps({"entityId": "SUB-001", "status": "Cancelled", "timestamp": "2025-06-02T10:00:00Z"})
        result = json.loads(invoke(detect_conflicts, current_sf_record_json=sf, incoming_payload_json=incoming))
        assert any("STATUS_CONFLICT" in c for c in result["conflicts"])
        assert result["severity"] == "CRITICAL"
