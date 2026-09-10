"""
Excess Usage review -- SRV-004 (Nico's, or Cherish's, decision, always
recorded with a reason), SRV-013 (treatment categories), and SRV-006/
SRV-008 (a billable decision must proceed to invoicing, at the
contract's blended rate).
"""
import uuid
from datetime import datetime, timezone

from sqlalchemy.orm import Session

from app.models.billing import Invoice
from app.models.contracts import Contract, ExcessTreatment, ExcessUsageRecord
from app.models.core import User
from app.services import audit, billing
from app.services.contracts import ContractRuleViolation
from app.services.timesheets import EXCESS_REVIEWER_ROLES


def decide_excess_usage(
    db: Session,
    excess_record: ExcessUsageRecord,
    contract: Contract,
    *,
    treatment: ExcessTreatment,
    reason: str,
    reviewer: User,
) -> Invoice | None:
    if reviewer.role not in EXCESS_REVIEWER_ROLES:
        raise ContractRuleViolation(
            "Only Nico (service_lead), Cherish as backup (sales_manager), or "
            "Dennis (owner) may decide excess usage treatment (SRV-004/SRV-011)."
        )
    if excess_record.is_decided:
        raise ContractRuleViolation("This excess usage has already been decided.")
    if not reason or not reason.strip():
        # SRV-004: "The decision and reason must be auditable" -- a reason
        # is not optional.
        raise ContractRuleViolation("A reason is required for every excess usage decision (SRV-004).")

    excess_record.treatment = treatment
    excess_record.reason = reason.strip()
    excess_record.decided_by_user_id = reviewer.id
    excess_record.decided_at = datetime.now(timezone.utc)
    db.flush()

    audit.record(
        db,
        entity_type="excess_usage_record",
        entity_id=excess_record.id,
        action="decided",
        actor_user_id=reviewer.id,
        reason=reason,
        details=f"treatment={treatment.value}",
    )

    invoice = None
    if treatment == ExcessTreatment.BILLABLE:
        # SRV-006/SRV-008: billable excess must proceed to invoicing, at
        # the contract's blended rate, no customer pre-approval needed.
        invoice = billing.issue_excess_usage_invoice(
            db, excess_record, contract, actor_user_id=reviewer.id
        )

    return invoice
