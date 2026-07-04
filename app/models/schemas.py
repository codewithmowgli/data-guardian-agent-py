from pydantic import BaseModel, Field
from enum import Enum
from typing import Optional
from datetime import datetime


class GuardianDecision(str, Enum):
    APPROVE = "APPROVE"
    REJECT = "REJECT"
    QUARANTINE = "QUARANTINE"
    ESCALATE_TO_HUMAN = "ESCALATE_TO_HUMAN"


class GuardianEvent(BaseModel):
    event_id: str = Field(..., description="Unique event identifier")
    source_system: str = Field(..., description="PARTNER_PORTAL | LUCID_COM | SUBSCRIPTION_APP | LUCID_FINANCE | SAP")
    entity_type: str = Field(..., description="LEAD | ORDER | INVOICE | SUBSCRIPTION | VEHICLE_CONFIG")
    entity_id: str = Field(..., description="Entity identifier")
    action: str = Field(..., description="UPSERT | DELETE")
    payload_json: str = Field(..., description="Serialized entity payload")
    timestamp: str = Field(default_factory=lambda: datetime.utcnow().isoformat())


class ValidationResult(BaseModel):
    valid: bool
    errors: list[str] = []
    warnings: list[str] = []


class FieldConflict(BaseModel):
    field_name: str
    current_value: str
    incoming_value: str
    conflict_type: str  # VALUE_MISMATCH | STALE_UPDATE | DUPLICATE | BUSINESS_RULE


class ConflictReport(BaseModel):
    has_conflicts: bool
    conflict_count: int = 0
    severity: str = "NONE"  # NONE | LOW | MEDIUM | HIGH | CRITICAL
    conflicts: list[str] = []


class ResolveRequest(BaseModel):
    resolution: GuardianDecision
    resolved_by: str
