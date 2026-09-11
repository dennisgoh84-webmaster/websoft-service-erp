"""
Service Records business logic (formerly "Timesheets"): SRV-007
rounding, SRV-015 missing-record flagging, and the SRV-003/SRV-004
contract-hour validation that decides Contract Deduction vs. Excess
Review on approval.

Confirmed 2026-09-11: the approver keys in the actual deduction minutes
at approval time (distinct from the objective raw/rounded log), and a
Job Order auto-closes once its most recent Service Record is both
Approved and marked Completed. See approve_service_record() and
maybe_auto_close_job_order() below.
"""
import math
import uuid
from datetime import date, datetime, timezone

from sqlalchemy.orm import Session

from app.models.contracts import ContractKind, ExcessUsageRecord
from app.models.core import User, UserRole
from app.models.job_orders import JobOrder, JobOrderStatus
from app.models.service_records import (
    ServiceRecord,
    ServiceRecordCompletion,
    ServiceRecordOutcome,
    ServiceRecordStatus,
    round_up_to_nearest,
)
from app.services import audit
from app.services.contracts import ContractRuleViolation, deduct_minutes
from app.services.numbering import next_document_number

# Pragmatic default pending open decision 9.1 (who approves Service
# Records, and within what timeframe) -- deferred for now at the user's
# request. Revisit once that is decided.
SERVICE_RECORD_APPROVER_ROLES = {UserRole.SERVICE_LEAD, UserRole.SALES_MANAGER, UserRole.OWNER}
# SRV-004/SRV-011: excess usage is reviewed by Nico (service lead) or,
# as backup, Cherish (sales manager). Owner (Dennis) can also act.
EXCESS_REVIEWER_ROLES = {UserRole.SERVICE_LEAD, UserRole.SALES_MANAGER, UserRole.OWNER}

# Confirmed 2026-09-11: Urgent x1.5, After-Office-Hours/Weekend/Holiday
# x2.0. When a record is both, the higher one wins rather than the two
# multiplying together (confirmed default -- flagged as a default, not
# an explicitly confirmed rule, in docs/open-business-decisions.md).
URGENT_MULTIPLIER = 1.5
AFTER_HOURS_MULTIPLIER = 2.0


def suggested_deduction_minutes(*, rounded_minutes: int, is_urgent: bool, is_after_hours: bool) -> int:
    """Only ever a *suggestion* prefilled on the Service Record Approval
    form -- the approver can key in any value regardless (confirmed
    2026-09-11: "actual is 240mins, deducted is 220mins or 360mins")."""
    multiplier = 1.0
    if is_urgent:
        multiplier = max(multiplier, URGENT_MULTIPLIER)
    if is_after_hours:
        multiplier = max(multiplier, AFTER_HOURS_MULTIPLIER)
    return math.ceil(rounded_minutes * multiplier)


def submit_service_record(
    db: Session,
    *,
    job_order_id: uuid.UUID,
    employee_user_id: uuid.UUID,
    work_date: date,
    raw_minutes: int,
    completion_status: ServiceRecordCompletion = ServiceRecordCompletion.UNCOMPLETED,
    is_after_hours: bool = False,
) -> ServiceRecord:
    job_order = db.get(JobOrder, job_order_id)
    if job_order is None:
        raise ContractRuleViolation("Job order not found.")
    if job_order.status in (JobOrderStatus.CLOSED, JobOrderStatus.VOID):
        raise ContractRuleViolation(f"Job order is {job_order.status.value}; reopen it first.")

    record = ServiceRecord(
        # Multi-company: a service record belongs to the same company as
        # the job order the work was logged against.
        company_id=job_order.company_id,
        service_record_number=next_document_number(
            db, company_id=job_order.company_id, doc_kind="service_record"
        ),
        job_order_id=job_order_id,
        employee_user_id=employee_user_id,
        work_date=work_date,
        raw_minutes=raw_minutes,
        rounded_minutes=round_up_to_nearest(raw_minutes),  # SRV-007
        status=ServiceRecordStatus.SUBMITTED,
        outcome=ServiceRecordOutcome.PENDING,
        completion_status=completion_status,
        is_after_hours=is_after_hours,
    )
    db.add(record)
    db.flush()

    audit.record(
        db,
        entity_type="service_record",
        entity_id=record.id,
        action="submitted",
        actor_user_id=employee_user_id,
        details=(
            f"raw_minutes={raw_minutes}, rounded_minutes={record.rounded_minutes}, "
            f"completion_status={completion_status.value}, is_after_hours={is_after_hours}"
        ),
    )
    return record


def maybe_auto_close_job_order(db: Session, job_order: JobOrder, *, actor: User) -> bool:
    """Confirmed 2026-09-11: a Job Order auto-closes when its most
    recently submitted Service Record is Approved AND marked Completed
    ('C', not Uncompleted 'U') -- only the latest record matters, so
    earlier "more visits needed" (U) records don't block closing once
    the final visit is done. Returns True if this call closed it."""
    if job_order.status not in (JobOrderStatus.OPEN, JobOrderStatus.ASSIGNED):
        return False

    latest = (
        db.query(ServiceRecord)
        .filter(ServiceRecord.job_order_id == job_order.id)
        .order_by(ServiceRecord.work_date.desc(), ServiceRecord.submitted_at.desc())
        .first()
    )
    if latest is None:
        return False
    if latest.status != ServiceRecordStatus.APPROVED:
        return False
    if latest.completion_status != ServiceRecordCompletion.COMPLETED:
        return False

    old_status = job_order.status
    job_order.status = JobOrderStatus.CLOSED
    job_order.closed_at = datetime.now(timezone.utc)
    audit.record(
        db,
        entity_type="job_order",
        entity_id=job_order.id,
        action="auto_closed",
        actor_user_id=actor.id,
        old_value={"status": old_status.value},
        new_value={"status": job_order.status.value},
        details=f"triggered by service_record={latest.id} (last record, Approved + Completed)",
    )
    db.flush()
    return True


def approve_service_record(
    db: Session,
    record: ServiceRecord,
    job_order: JobOrder,
    *,
    approver: User,
    deducted_minutes: int,
) -> ExcessUsageRecord | None:
    if approver.role not in SERVICE_RECORD_APPROVER_ROLES:
        raise ContractRuleViolation(
            "This user's role cannot approve Service Records (pending decision on "
            "open item 9.1; current default roles: service_lead, sales_manager, owner)."
        )
    if record.status != ServiceRecordStatus.SUBMITTED:
        raise ContractRuleViolation("Only a submitted Service Record can be approved.")
    if deducted_minutes <= 0:
        raise ContractRuleViolation("Deducted minutes must be greater than zero.")
    if job_order.contract_id is None:
        raise ContractRuleViolation(
            "This job order has no linked Service Contract; contract-hour validation "
            "requires one for this build's scope."
        )

    record.status = ServiceRecordStatus.APPROVED
    record.approved_at = datetime.now(timezone.utc)
    record.approved_by_user_id = approver.id
    record.deducted_minutes = deducted_minutes

    contract = job_order.contract
    deduct_amount = deducted_minutes

    excess_record: ExcessUsageRecord | None = None

    if contract.contract_kind in (ContractKind.ANNUAL, ContractKind.AD_HOC):
        # Confirmed 2026-09-10 (ANNUAL) / 2026-09-11 (AD_HOC): neither
        # has an hour pool, so there is nothing to deduct or exceed --
        # the work is simply covered under the contract's term (ANNUAL)
        # or billed manually off its reference rate (AD_HOC).
        record.outcome = ServiceRecordOutcome.NOT_HOUR_METERED
        audit.record(
            db,
            entity_type="service_record",
            entity_id=record.id,
            action="approved",
            actor_user_id=approver.id,
            details=f"outcome={record.outcome.value}, deducted_minutes={deducted_minutes} (not hour-metered)",
        )
        db.flush()
        maybe_auto_close_job_order(db, job_order, actor=approver)
        return None

    remaining = contract.remaining_minutes

    if remaining >= deduct_amount:
        # SRV-003: hours remain -- straightforward contract deduction.
        deduct_minutes(db, contract, deduct_amount, actor_user_id=approver.id)
        record.outcome = ServiceRecordOutcome.CONTRACT_DEDUCTION
    else:
        # SRV-003: no grace period. Deduct whatever balance remains (may be
        # zero) and the rest becomes Excess Usage immediately -- never a
        # negative balance (SRV-004).
        if remaining > 0:
            deduct_minutes(db, contract, remaining, actor_user_id=approver.id)
        excess_minutes = deduct_amount - remaining
        excess_record = ExcessUsageRecord(
            company_id=contract.company_id,
            contract_id=contract.id,
            service_record_id=record.id,
            excess_minutes=excess_minutes,
        )
        db.add(excess_record)
        record.outcome = ServiceRecordOutcome.EXCESS_USAGE
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
        entity_type="service_record",
        entity_id=record.id,
        action="approved",
        actor_user_id=approver.id,
        details=f"outcome={record.outcome.value}, deducted_minutes={deducted_minutes}",
    )
    db.flush()
    maybe_auto_close_job_order(db, job_order, actor=approver)
    return excess_record
