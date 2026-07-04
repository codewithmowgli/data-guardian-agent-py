from sqlalchemy import create_engine, Column, String, Text, DateTime, Enum as SAEnum
from sqlalchemy.orm import declarative_base, sessionmaker
from sqlalchemy.dialects.postgresql import UUID
from datetime import datetime
import uuid

from app.config.settings import settings
from app.models.schemas import GuardianDecision

engine = create_engine(settings.database_url)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()


class AuditLog(Base):
    __tablename__ = "guardian_audit_log"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    event_id = Column(String(100), nullable=False)
    source_system = Column(String(50), nullable=False)
    entity_type = Column(String(50), nullable=False)
    entity_id = Column(String(100))
    action = Column(String(20), nullable=False)
    incoming_payload = Column(Text)
    sf_snapshot = Column(Text)
    conflicts_detected = Column(Text)
    llm_reasoning = Column(Text)
    decision = Column(SAEnum(GuardianDecision), nullable=False)
    decision_detail = Column(Text)
    sf_record_id = Column(String(20))
    jira_ticket_id = Column(String(20))
    created_at = Column(DateTime, default=datetime.utcnow)
    resolved_at = Column(DateTime, nullable=True)
    resolved_by = Column(String(100), nullable=True)


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def init_db():
    Base.metadata.create_all(bind=engine)
