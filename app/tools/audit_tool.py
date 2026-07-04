import logging
import time
from langchain_core.tools import tool
from sqlalchemy.orm import Session

from app.models.database import AuditLog, SessionLocal
from app.models.schemas import GuardianDecision

logger = logging.getLogger(__name__)


@tool
def create_audit_entry(
    event_id: str,
    source_system: str,
    entity_type: str,
    entity_id: str,
    action: str,
    incoming_payload: str,
    sf_snapshot: str,
    conflicts_json: str,
    llm_reasoning: str,
    decision: str,
    decision_detail: str
) -> str:
    """Create a full audit log entry with LLM reasoning trace and final decision. Always call this for every event."""
    logger.info(f"[AUDIT-TOOL] Creating audit entry: eventId={event_id}, decision={decision}")

    db: Session = SessionLocal()
    try:
        audit = AuditLog(
            event_id=event_id,
            source_system=source_system,
            entity_type=entity_type,
            entity_id=entity_id,
            action=action,
            incoming_payload=incoming_payload,
            sf_snapshot=sf_snapshot,
            conflicts_detected=conflicts_json,
            llm_reasoning=llm_reasoning,
            decision=GuardianDecision(decision),
            decision_detail=decision_detail
        )
        db.add(audit)
        db.commit()
        db.refresh(audit)
        logger.info(f"[AUDIT-TOOL] Audit entry saved: id={audit.id}")
        return f'{{"success": true, "auditId": "{audit.id}"}}'
    except Exception as e:
        db.rollback()
        logger.error(f"[AUDIT-TOOL] Failed to save audit: {e}")
        return f'{{"success": false, "error": "{str(e)}"}}'
    finally:
        db.close()


@tool
def quarantine_record(entity_id: str, source_system: str, reason: str, payload_json: str) -> str:
    """Quarantine a record that has conflicts requiring human review."""
    logger.warning(f"[AUDIT-TOOL] QUARANTINING record: entityId={entity_id}, source={source_system}, reason={reason}")

    db: Session = SessionLocal()
    try:
        quarantine = AuditLog(
            event_id=f"QUARANTINE-{int(time.time())}",
            source_system=source_system,
            entity_type="QUARANTINED",
            entity_id=entity_id,
            action="QUARANTINE",
            incoming_payload=payload_json,
            decision=GuardianDecision.QUARANTINE,
            decision_detail=reason
        )
        db.add(quarantine)
        db.commit()
        return f'{{"quarantined": true, "entityId": "{entity_id}", "reason": "{reason}"}}'
    finally:
        db.close()
