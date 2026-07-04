import json
from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.agent.orchestrator import process_event
from app.models.database import get_db, AuditLog
from app.models.schemas import GuardianEvent, GuardianDecision, ResolveRequest

router = APIRouter(prefix="/api/v1/guardian", tags=["Data Guardian Agent"])


@router.post("/process", summary="Manually trigger the guardian agent for a data event")
def process(event: GuardianEvent):
    result = process_event(event.model_dump_json())
    return {"result": result}


@router.get("/audit/{entity_id}", summary="Get full audit history for a Salesforce entity")
def get_audit_history(entity_id: str, db: Session = Depends(get_db)):
    logs = db.query(AuditLog).filter(
        AuditLog.entity_id == entity_id
    ).order_by(AuditLog.created_at.desc()).all()
    return logs


@router.get("/quarantine", summary="List all quarantined records pending human review")
def get_quarantined(db: Session = Depends(get_db)):
    records = db.query(AuditLog).filter(
        AuditLog.decision == GuardianDecision.QUARANTINE,
        AuditLog.resolved_at.is_(None)
    ).order_by(AuditLog.created_at.desc()).all()
    return records


@router.post("/quarantine/{record_id}/resolve", summary="Resolve a quarantined record")
def resolve_quarantine(record_id: str, request: ResolveRequest, db: Session = Depends(get_db)):
    record = db.query(AuditLog).filter(AuditLog.id == record_id).first()
    if not record:
        raise HTTPException(status_code=404, detail="Record not found")
    record.decision = request.resolution
    record.resolved_at = datetime.utcnow()
    record.resolved_by = request.resolved_by
    db.commit()
    return {"resolved": True, "resolution": request.resolution}


@router.get("/health/systems", summary="Last seen timestamp per source system")
def system_health(db: Session = Depends(get_db)):
    systems = ["PARTNER_PORTAL", "LUCID_COM", "SUBSCRIPTION_APP", "LUCID_FINANCE", "SAP"]
    health = {}
    for system in systems:
        last = db.query(AuditLog).filter(
            AuditLog.source_system == system
        ).order_by(AuditLog.created_at.desc()).first()
        health[system] = str(last.created_at) if last else "NO_EVENTS_YET"
    return health


@router.get("/metrics/summary", summary="Decision breakdown — approval rate, conflicts, escalations")
def metrics_summary(db: Session = Depends(get_db)):
    summary = {}
    for decision in GuardianDecision:
        count = db.query(AuditLog).filter(AuditLog.decision == decision).count()
        summary[decision.value] = count
    return summary
