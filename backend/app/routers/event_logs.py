"""
Event Logs -- the security-gated master over the central audit trail
(app.models.core.AuditLogEntry / app.services.audit). Read-only: this
module lets an authorized group see who did what, when, from where,
and (for edits) the field-level before/after values -- it never writes
audit entries of its own except when a report/export is generated.
"""
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
from app.services import audit, exports
from app.services.authority import require_module_access

router = APIRouter(prefix="/api/event-logs", tags=["event-logs"])
MODULE = "event_logs"

EVENT_LOG_EXPORT_FIELDS = [
    "when", "actor", "action", "entity_type", "entity_id", "old_value", "new_value",
    "reason", "details", "ip_address", "device_id", "user_agent",
]


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


def _event_logs_for_export(
    db: Session,
    company_id: uuid.UUID,
    entity_type: str | None,
    action: str | None,
    actor_user_id: uuid.UUID | None,
    date_from: date | None,
    date_to: date | None,
    q: str | None,
) -> list[AuditLogEntry]:
    query = _apply_filters(
        # Multi-company: each company sees only its own trail. Entries
        # written before company stamping existed carry a null
        # company_id and are shown to everyone rather than hidden.
        db.query(AuditLogEntry).filter(
            or_(
                AuditLogEntry.company_id == company_id,
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
    return query.order_by(AuditLogEntry.at.desc()).limit(5000).all()


def _event_log_row(r: AuditLogEntry) -> dict:
    return {
        "when": r.at.isoformat(),
        "actor": r.actor_name or "",
        "action": r.action,
        "entity_type": r.entity_type,
        "entity_id": str(r.entity_id),
        "old_value": r.old_value or "",
        "new_value": r.new_value or "",
        "reason": r.reason or "",
        "details": r.details or "",
        "ip_address": r.ip_address or "",
        "device_id": r.device_id or "",
        "user_agent": r.user_agent or "",
    }


def _record_export_event(
    db: Session,
    current_user: User,
    row_count: int,
    fmt: str,
    entity_type: str | None,
    action: str | None,
    actor_user_id: uuid.UUID | None,
    date_from: date | None,
    date_to: date | None,
    q: str | None,
) -> None:
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
        details=f"Event Log {fmt.upper()} export -- {row_count} rows, filters: {filters_desc}",
    )
    db.commit()


@router.get("/export.csv")
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
    rows = _event_logs_for_export(
        db, current_user.company_id, entity_type, action, actor_user_id, date_from, date_to, q
    )
    csv_text = exports.rows_to_csv(EVENT_LOG_EXPORT_FIELDS, [_event_log_row(r) for r in rows])
    _record_export_event(
        db, current_user, len(rows), "csv", entity_type, action, actor_user_id, date_from, date_to, q
    )
    return StreamingResponse(
        iter([csv_text]),
        media_type="text/csv",
        headers={"Content-Disposition": "attachment; filename=event-log-export.csv"},
    )


@router.get("/export.xlsx")
def export_event_logs_excel(
    entity_type: str | None = None,
    action: str | None = None,
    actor_user_id: uuid.UUID | None = None,
    date_from: date | None = None,
    date_to: date | None = None,
    q: str | None = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_module_access(MODULE, AccessLevel.VIEW)),
):
    rows = _event_logs_for_export(
        db, current_user.company_id, entity_type, action, actor_user_id, date_from, date_to, q
    )
    data = exports.rows_to_excel(EVENT_LOG_EXPORT_FIELDS, [_event_log_row(r) for r in rows], sheet_name="Event Logs")
    _record_export_event(
        db, current_user, len(rows), "excel", entity_type, action, actor_user_id, date_from, date_to, q
    )
    return StreamingResponse(
        iter([data]),
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": "attachment; filename=event-log-export.xlsx"},
    )
