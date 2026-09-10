"""
Service Records business logic (formerly "Timesheets"): SRV-007
rounding, SRV-015 missing-record flagging, and the SRV-003/SRV-004
contract-hour validation that decides Contract Deduction vs. Excess
Review on approval.
"""
import uuid
from datetime import date, datetime, timezone

from sqlalchemy.orm import Session

from app.models.contracts import ContractKind, ExcessUsageRecord
from app.models.core import User, UserRole
from app.models.job_orders import JobOrder
from app.models.service_records import (
    ServiceRecord,
    ServiceRecordOutcome,
    ServiceRecordStatus,
    round_up_to_nearest,
)
from app.services import audit
from app.services.contracts import ContractRuleViolation, deduct_minutes

# Pragmatic default pending open decision 9.1 (who approves Service
# Records, and within what timeframe) -- deferred for now at the user's
# request. Revisit once that is decided.
SERVICE_RECORD_APPROVER_ROLES = {UserRole.SERVICE_LEAD, UserRole.SALES_MANAGER, UserRole.OWNER}
# SRV-004/SRV-011: excess usage is reviewed by Nico (service lead) or,
# as backup, Cherish (sales manager). Owner (Dennis) can also act.
EXCESS_REVIEWER_ROLES = {UserRole.SERVICE_LEAD, UserRole.SALES_MANAGER, UserRole.OWNER}


def submit_service_record(
    db: Session,
    *,
    job_order_id: uuid.UUID,
    employee_user_id: uuid.UUID,
    work_date: date,
    raw_minutes: int,
) -> ServiceRecord:
    job_order = db.get(JobOrder, job_order_id)
    if job_order is None:
        raise ContractRuleViolation("Job order not found.")

    record = ServiceRecord(
        # Multi-company: a service record belongs to the same company as
        # the job order the work was logged against.
        company_id=job_order.company_id,
        job_order_id=job_order_id,
        employee_user_id=employee_user_id,
        work_date=work_date,
        raw_minutes=raw_minutes,
        rounded_minutes=round_up_to_nearest(raw_minutes),  # SRV-007
        status=ServiceRecordStatus.SUBMITTED,
        outcome=ServiceRecordOutcome.PENDING,
    )
    db.add(record)
    db.flush()

    audit.record(
        db,
        entity_type="service_record",
        entity_id=record.id,
        action="submitted",
        actor_user_id=employee_user_id,
        details=f"raw_minutes={raw_minutes}, rounded_minutes={record.rounded_minutes}",
    )
    return record


def approve_service_record(
    db: Session,
    record: ServiceRecord,
    job_order: JobOrder,
    *,
    approver: User,
) -> ExcessUsageRecord | None:
    if approver.role not in SERVICE_RECORD_APPROVER_ROLES:
        raise ContractRuleViolation(
            "This user's role cannot approve Service Records (pending decision on "
            "open item 9.1; current default roles: service_lead, sales_manager, owner)."
        )
    if record.status != ServiceRecordStatus.SUBMITTED:
        raise ContractRuleViolation("Only a submitted Service Record can be approved.")
    if job_order.contract_id is None:
        raise ContractRuleViolation(
            "This job order has no linked Service Contract; contract-hour validation "
            "requires one for this build's scope."
        )

    record.status = ServiceRecordStatus.APPROVED
    record.approved_at = datetime.now(timezone.utc)
    record.approved_by_user_id = approver.id

    contract = job_order.contract
    rounded = record.rounded_minutes

    excess_record: ExcessUsageRecord | None = None

    if contract.contract_kind == ContractKind.ANNUAL:
        # Confirmed 2026-09-10: an ANNUAL (term-only) contract has no
        # hour pool, so there is nothing to deduct or exceed -- the
        # work is simply covered under the contract's term.
        record.outcome = ServiceRecordOutcome.NOT_HOUR_METERED
        audit.record(
            db,
            entity_type="service_record",
            entity_id=record.id,
            action="approved",
            actor_user_id=approver.id,
            details=f"outcome={record.outcome.value}",
        )
        db.flush()
        return None

    remaining = contract.remaining_minutes

    if remaining >= rounded:
        # SRV-003: hours remain -- straightforward contract deduction.
        deduct_minutes(db, contract, rounded, actor_user_id=approver.id)
        record.outcome = ServiceRecordOutcome.CONTRACT_DEDUCTION
    else:
        # SRV-003: no grace period. Deduct whatever balance remains (may be
        # zero) and the rest becomes Excess Usage immediately -- never a
        # negative balance (SRV-004).
        if remaining > 0:
            deduct_minutes(db, contract, remaining, actor_user_id=approver.id)
        excess_minutes = rounded - remaining
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
        details=f"outcome={record.outcome.value}",
    )
    db.flush()
    return excess_record
