"""Central audit logging helper -- every module writes through here
rather than each inventing its own logging, per the architecture in
docs/system-architecture.md (Audit logging section)."""
import uuid

from sqlalchemy.orm import Session

from app.models.core import AuditLogEntry


def record(
    db: Session,
    *,
    entity_type: str,
    entity_id: uuid.UUID,
    action: str,
    actor_user_id: uuid.UUID | None,
    reason: str | None = None,
    details: str | None = None,
) -> AuditLogEntry:
    entry = AuditLogEntry(
        entity_type=entity_type,
        entity_id=entity_id,
        action=action,
        actor_user_id=actor_user_id,
        reason=reason,
        details=details,
    )
    db.add(entry)
    return entry
