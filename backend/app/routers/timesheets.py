import uuid

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.deps import get_current_user
from app.models.core import User
from app.models.tickets import HelpdeskTicket
from app.models.timesheets import TimesheetEntry
from app.schemas.schemas import TimesheetCreate, TimesheetOut
from app.services import timesheets as ts_svc

router = APIRouter(prefix="/api/timesheets", tags=["timesheets"])


@router.post("", response_model=TimesheetOut)
def submit_timesheet(
    payload: TimesheetCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    entry = ts_svc.submit_timesheet_entry(
        db,
        ticket_id=payload.ticket_id,
        employee_user_id=payload.employee_user_id,
        work_date=payload.work_date,
        raw_minutes=payload.raw_minutes,
    )
    db.commit()
    db.refresh(entry)
    return entry


@router.get("", response_model=list[TimesheetOut])
def list_timesheets(
    ticket_id: uuid.UUID | None = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    query = db.query(TimesheetEntry)
    if ticket_id:
        query = query.filter(TimesheetEntry.ticket_id == ticket_id)
    return query.all()


@router.post("/{entry_id}/approve", response_model=TimesheetOut)
def approve_timesheet(
    entry_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    entry = db.get(TimesheetEntry, entry_id)
    if not entry:
        raise HTTPException(status_code=404, detail="Timesheet entry not found")
    ticket = db.get(HelpdeskTicket, entry.ticket_id)
    try:
        ts_svc.approve_timesheet_entry(db, entry, ticket, approver=current_user)
    except ts_svc.ContractRuleViolation as e:
        raise HTTPException(status_code=422, detail=str(e))
    db.commit()
    db.refresh(entry)
    return entry
