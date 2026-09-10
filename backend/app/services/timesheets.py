"""
Timesheets business logic: SRV-007 rounding, SRV-015 missing-timesheet
flagging, and the SRV-003/SRV-004 contract-hour validation that decides
Contract Deduction vs. Excess Review on approval.
"""
import uuid
from datetime import date, datetime, timezone

from sqlalchemy.orm import Session

from app.models.contracts import ExcessUsageRecord
from app.models.core import UserRole
from app.models.tickets import HelpdeskTicket
from app.models.timesheets import (
    TimesheetEntry,
    TimesheetOutcome,
    TimesheetStatus,
    round_up_to_nearest,
)
from app.models.core import User
from app.services import audit
from app.services.contracts import ContractRuleViolation, deduct_minutes

# Pragmatic default pending open decision 9.1 (who approves timesheets,
# and within what timeframe). Revisit once that is decided.
TIMESHEET_APPROVER_ROLES = {UserRole.SERVICE_LEAD, UserRole.SALES_MANAGER, UserRole.OWNER}
# SRV-004/SRV-011: excess usage is reviewed by Nico (service lead) or,
# as backup, Cherish (sales manager). Owner (Dennis) can also act.
EXCESS_REVIEWER_ROLES = {UserRole.SERVICE_LEAD, UserRole.SALES_MANAGER, UserRole.OWNER}


def submit_timesheet_entry(
    db: Session,
    *,
    ticket_id: uuid.UUID,
    employee_user_id: uuid.UUID,
    work_date: date,
    raw_minutes: int,
) -> TimesheetEntry:
    entry = TimesheetEntry(
        ticket_id=ticket_id,
        employee_user_id=employee_user_id,
        work_date=work_date,
        raw_minutes=raw_minutes,
        rounded_minutes=round_up_to_nearest(raw_minutes),  # SRV-007
        status=TimesheetStatus.SUBMITTED,
        outcome=TimesheetOutcome.PENDING,
    )
    db.add(entry)
    db.flush()

    audit.record(
        db,
        entity_type="timesheet_entry",
        entity_id=entry.id,
        action="submitted",
        actor_user_id=employee_user_id,
        details=f"raw_minutes={raw_minutes}, rounded_minutes={entry.rounded_minutes}",
    )
    return entry


def approve_timesheet_entry(
    db: Session,
    entry: TimesheetEntry,
    ticket: HelpdeskTicket,
    *,
    approver: User,
) -> ExcessUsageRecord | None:
    if approver.role not in TIMESHEET_APPROVER_ROLES:
        raise ContractRuleViolation(
            "This user's role cannot approve timesheets (pending decision on "
            "open item 9.1; current default roles: service_lead, sales_manager, owner)."
        )
    if entry.status != TimesheetStatus.SUBMITTED:
        raise ContractRuleViolation("Only a submitted timesheet entry can be approved.")
    if ticket.contract_id is None:
        raise ContractRuleViolation(
            "This ticket has no linked Service Contract; contract-hour validation "
            "requires one for this build's scope."
        )

    entry.status = TimesheetStatus.APPROVED
    entry.approved_at = datetime.now(timezone.utc)
    entry.approved_by_user_id = approver.id

    contract = ticket.contract
    remaining = contract.remaining_minutes
    rounded = entry.rounded_minutes

    excess_record: ExcessUsageRecord | None = None

    if remaining >= rounded:
        # SRV-003: hours remain -- straightforward contract deduction.
        deduct_minutes(db, contract, rounded, actor_user_id=approver.id)
        entry.outcome = TimesheetOutcome.CONTRACT_DEDUCTION
    else:
        # SRV-003: no grace period. Deduct whatever balance remains (may be
        # zero) and the rest becomes Excess Usage immediately -- never a
        # negative balance (SRV-004).
        if remaining > 0:
            deduct_minutes(db, contract, remaining, actor_user_id=approver.id)
        excess_minutes = rounded - remaining
        excess_record = ExcessUsageRecord(
            contract_id=contract.id,
            timesheet_entry_id=entry.id,
            excess_minutes=excess_minutes,
        )
        db.add(excess_record)
        entry.outcome = TimesheetOutcome.EXCESS_USAGE
        db.flush()

        audit.record(
            db,
            entity_type="excess_usage_record",
            entity_id=excess_record.id,
            action="created",
            actor_user_id=approver.id,
            details=f"excess_minutes={excess_minutes}, awaiting_review=True",
        )

    audit.record(
        db,
        entity_type="timesheet_entry",
        entity_id=entry.id,
        action="approved",
        actor_user_id=approver.id,
        details=f"outcome={entry.outcome.value}",
    )
    db.flush()
    return excess_record
