"""
Event Logs -- the security-gated master over the central audit trail
(app.models.core.AuditLogEntry / app.services.audit). Read-only: this
module lets an authorized group see who did what, when, from where,
and (for edits) the field-level before/after values -- it never writes
audit entries of its own except when a report/export is generated.
"""
import csv
import io
import uuid
from datetime import date, datetime, timedelta

from fastapi import APIRouter, Depends
from fastapi.responses import StreamingResponse
from sqlalchemy import or_
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.models.core import AuditLogEntry, User
from app.models.groups import AccessLevel
from app.schemas.schemas import AuditLogEntryOut
from app.services import audit
from app.services.authority import require_module_access

router = APIRouter(prefix="/api/event-logs", tags=["event-logs"])
MODULE = "event_logs"


def _apply_filters(
    query,
    *,
    entity_type: str | None,
    action: str | None,
    actor_user_id: uuid.UUID | None,
    date_from: date | None,
    date_to: date | None,
    q: str | None,
):
    if entity_type:
        query = query.filter(AuditLogEntry.entity_type == entity_type)
    if action:
        query = query.filter(AuditLogEntry.action == action)
    if actor_user_id:
        query = query.filter(AuditLogEntry.actor_user_id == actor_user_id)
    if date_from:
        query = query.filter(AuditLogEntry.at >= datetime.combine(date_from, datetime.min.time()))
    if date_to:
        query = query.filter(AuditLogEntry.at < datetime.combine(date_to + timedelta(days=1), datetime.min.time()))
    if q:
        like = f"%{q}%"
        query = query.filter(
            or_(
                AuditLogEntry.details.ilike(like),
                AuditLogEntry.reason.ilike(like),
                AuditLogEntry.actor_name.ilike(like),
                AuditLogEntry.entity_type.ilike(like),
                AuditLogEntry.action.ilike(like),
            )
        )
    return query


@router.get("", response_model=list[AuditLogEntryOut])
def list_event_logs(
    entity_type: str | None = None,
    action: str | None = None,
    actor_user_id: uuid.UUID | None = None,
    date_from: date | None = None,
    date_to: date | None = None,
    q: str | None = None,
    limit: int = 100,
    offset: int = 0,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_module_access(MODULE, AccessLevel.VIEW)),
):
    query = _apply_filters(
        # Multi-company: each company sees only its own trail. Entries
        # written before company stamping existed carry a null
        # company_id and are shown to everyone rather than hidden.
        db.query(AuditLogEntry).filter(
            or_(
                AuditLogEntry.company_id == current_user.company_id,
                AuditLogEntry.company_id.is_(None),
            )
        ),
        entity_type=entity_type,
        action=action,
        actor_user_id=actor_user_id,
        date_from=date_from,
        date_to=date_to,
        q=q,
    )
    return (
        query.order_by(AuditLogEntry.at.desc())
        .offset(max(offset, 0))
        .limit(min(max(limit, 1), 500))
        .all()
    )


@router.get("/export")
def export_event_logs_csv(
    entity_type: str | None = None,
    action: str | None = None,
    actor_user_id: uuid.UUID | None = None,
    date_from: date | None = None,
    date_to: date | None = None,
    q: str | None = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_module_access(MODULE, AccessLevel.VIEW)),
):
    query = _apply_filters(
        # Multi-company: each company sees only its own trail. Entries
        # written before company stamping existed carry a null
        # company_id and are shown to everyone rather than hidden.
        db.query(AuditLogEntry).filter(
            or_(
                AuditLogEntry.company_id == current_user.company_id,
                AuditLogEntry.company_id.is_(None),
            )
        ),
        entity_type=entity_type,
        action=action,
        actor_user_id=actor_user_id,
        date_from=date_from,
        date_to=date_to,
        q=q,
    )
    rows = query.order_by(AuditLogEntry.at.desc()).limit(5000).all()

    buf = io.StringIO()
    writer = csv.writer(buf)
    writer.writerow(
        [
            "When",
            "Actor",
            "Action",
            "Entity type",
            "Entity ID",
            "Old value",
            "New value",
            "Reason",
            "Details",
            "IP address",
            "Device ID",
            "User agent",
        ]
    )
    for r in rows:
        writer.writerow(
            [
                r.at.isoformat(),
                r.actor_name or "",
                r.action,
                r.entity_type,
                str(r.entity_id),
                r.old_value or "",
                r.new_value or "",
                r.reason or "",
                r.details or "",
                r.ip_address or "",
                r.device_id or "",
                r.user_agent or "",
            ]
        )

    # The export itself is a reportable event: who ran it, with which
    # filters, and how many rows it returned.
    filters_desc = ", ".join(
        f"{k}={v}"
        for k, v in [
            ("entity_type", entity_type),
            ("action", action),
            ("actor_user_id", actor_user_id),
            ("date_from", date_from),
            ("date_to", date_to),
            ("q", q),
        ]
        if v
    ) or "none"
    audit.record_report_generated(
        db,
        actor_user_id=current_user.id,
        report_name="event_log_export",
        details=f"Event Log CSV export -- {len(rows)} rows, filters: {filters_desc}",
    )
    db.commit()

    buf.seek(0)
    return StreamingResponse(
        iter([buf.getvalue()]),
        media_type="text/csv",
        headers={"Content-Disposition": "attachment; filename=event-log-export.csv"},
    )
