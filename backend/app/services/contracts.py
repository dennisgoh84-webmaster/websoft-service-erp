"""
Service Contracts business logic -- the single place that enforces
SRV-001, SRV-002, SRV-005, SRV-010, SRV-012, SRV-014, SRV-016, SRV-018
(see docs/business-requirements.md for the confirmed rule text).

Per docs/system-architecture.md's Backend architecture section: "only
Service Contracts logic decides how contract hours are deducted" --
this module (plus services/service_records.py, which calls into it) is that
single place.
"""
import uuid
from dataclasses import dataclass
from datetime import date, datetime, timedelta, timezone

from dateutil.relativedelta import relativedelta
from sqlalchemy.orm import Session

from app.models.contracts import (
    MINIMUM_CONTRACTED_HOURS,
    PRE_EXPIRY_CHECK_LEAD_DAYS,
    RENEWAL_BACKDATING_WINDOW_DAYS,
    STANDARD_CONTRACT_MONTHS,
    Contract,
    ContractStatus,
    ExpiredHoursRecord,
)
from app.services import audit


class ContractRuleViolation(ValueError):
    """Raised when an action would violate a confirmed SRV rule."""


def create_contract(
    db: Session,
    *,
    company_id: uuid.UUID,
    customer_id: uuid.UUID,
    contracted_hours: float,
    contract_value_sgd: float,
    start_date: date,
    actor_user_id: uuid.UUID,
    renewed_from_contract_id: uuid.UUID | None = None,
) -> Contract:
    # SRV-002 / SRV-012: 10-hour hard minimum, no override mechanism.
    if contracted_hours < MINIMUM_CONTRACTED_HOURS:
        raise ContractRuleViolation(
            f"Contracted hours must be at least {MINIMUM_CONTRACTED_HOURS} "
            "(SRV-002). There is no override mechanism (SRV-012)."
        )

    # SRV-001: standard duration is 12 months, tracked start/end date.
    end_date = start_date + relativedelta(months=STANDARD_CONTRACT_MONTHS)

    contract = Contract(
        company_id=company_id,
        customer_id=customer_id,
        status=ContractStatus.DRAFT,
        contracted_minutes=int(contracted_hours * 60),
        consumed_minutes=0,
        contract_value_sgd=contract_value_sgd,
        start_date=start_date,
        end_date=end_date,
        renewed_from_contract_id=renewed_from_contract_id,
    )
    db.add(contract)
    db.flush()

    audit.record(
        db,
        entity_type="contract",
        entity_id=contract.id,
        action="created",
        actor_user_id=actor_user_id,
        details=f"contracted_hours={contracted_hours}, value_sgd={contract_value_sgd}",
    )
    return contract


def activate_contract(db: Session, contract: Contract, *, actor_user_id: uuid.UUID) -> Contract:
    if contract.status != ContractStatus.DRAFT:
        raise ContractRuleViolation("Only a Draft contract can be activated (SRV-001).")

    contract.status = ContractStatus.ACTIVE
    contract.activated_at = datetime.now(timezone.utc)
    db.flush()

    audit.record(
        db,
        entity_type="contract",
        entity_id=contract.id,
        action="activated",
        actor_user_id=actor_user_id,
    )
    return contract


def deduct_minutes(db: Session, contract: Contract, minutes: int, *, actor_user_id: uuid.UUID) -> None:
    """Reduce the contract's remaining balance. Caller (services/service_records.py)
    is responsible for ensuring `minutes` does not exceed the remaining
    balance -- SRV-004 requires the balance to never go negative."""
    if minutes > contract.remaining_minutes:
        raise ContractRuleViolation(
            "Cannot deduct more than the contract's remaining balance (SRV-004)."
        )
    contract.consumed_minutes += minutes

    # SRV-001: contract becomes "Exceeded" once fully consumed, even though
    # still within its 12-month term.
    if contract.remaining_minutes == 0 and contract.status == ContractStatus.ACTIVE:
        contract.status = ContractStatus.EXCEEDED
        audit.record(
            db,
            entity_type="contract",
            entity_id=contract.id,
            action="status_changed_to_exceeded",
            actor_user_id=actor_user_id,
        )
    db.flush()


def needs_pre_expiry_check(contract: Contract, as_of: date | None = None) -> bool:
    """SRV-014: the pre-expiry accounting check window starts 30 days
    before expiry."""
    as_of = as_of or date.today()
    return (
        contract.status in (ContractStatus.ACTIVE, ContractStatus.EXCEEDED)
        and 0 <= (contract.end_date - as_of).days <= PRE_EXPIRY_CHECK_LEAD_DAYS
    )


def expire_contract(db: Session, contract: Contract, *, actor_user_id: uuid.UUID) -> ExpiredHoursRecord | None:
    """SRV-005: forfeit all unused hours completely at expiry -- no
    roll-over, no credit, no transfer. Recorded, not deleted."""
    if contract.status not in (ContractStatus.ACTIVE, ContractStatus.EXCEEDED):
        raise ContractRuleViolation("Only an Active or Exceeded contract can expire.")

    remaining = contract.remaining_minutes
    record = None
    if remaining > 0:
        record = ExpiredHoursRecord(contract_id=contract.id, expired_minutes=remaining)
        db.add(record)

    contract.status = ContractStatus.EXPIRED
    db.flush()

    audit.record(
        db,
        entity_type="contract",
        entity_id=contract.id,
        action="expired",
        actor_user_id=actor_user_id,
        details=f"forfeited_minutes={remaining}",
    )
    return record


@dataclass
class RenewalEligibility:
    eligible_for_backdating: bool
    days_since_expiry: int


def check_renewal_eligibility(prior_contract: Contract, renewal_date: date | None = None) -> RenewalEligibility:
    """SRV-016: a renewal within 2 weeks of expiry is backdated (no
    coverage gap). Beyond that, SRV-018 applies: no fixed rule -- handled
    case-by-case by Nico, Cherish, or Dennis. This function only reports
    eligibility; it never auto-decides the SRV-018 case."""
    renewal_date = renewal_date or date.today()
    days_since_expiry = (renewal_date - prior_contract.end_date).days
    return RenewalEligibility(
        eligible_for_backdating=days_since_expiry <= RENEWAL_BACKDATING_WINDOW_DAYS,
        days_since_expiry=days_since_expiry,
    )


def renew_contract(
    db: Session,
    prior_contract: Contract,
    *,
    contracted_hours: float,
    contract_value_sgd: float,
    actor_user_id: uuid.UUID,
    renewal_date: date | None = None,
    force_start_date: date | None = None,
) -> Contract:
    """SRV-010: renewal creates a NEW contract record referencing the
    prior one, with its own fresh hour allocation (it never inherits the
    prior balance). SRV-016 governs whether it is backdated seamlessly;
    beyond that window (SRV-018) the caller must supply `force_start_date`
    explicitly (e.g. today), since there is no automatic rule for that
    case -- it is a case-by-case human decision.

    `renewal_date` defaults to today and only affects the SRV-016
    eligibility check (useful for testing or backdated data entry)."""
    eligibility = check_renewal_eligibility(prior_contract, renewal_date)

    if force_start_date is not None:
        start_date = force_start_date
    elif eligibility.eligible_for_backdating:
        start_date = prior_contract.end_date  # seamless, no coverage gap
    else:
        raise ContractRuleViolation(
            "Renewal is beyond the SRV-016 2-week backdating window "
            f"({eligibility.days_since_expiry} days since expiry). Per SRV-018 "
            "this must be a case-by-case decision by Nico, Cherish, or Dennis -- "
            "pass force_start_date explicitly to proceed."
        )

    if prior_contract.status not in (ContractStatus.EXPIRED, ContractStatus.EXCEEDED, ContractStatus.ACTIVE):
        raise ContractRuleViolation("Prior contract must be Active, Exceeded, or Expired to renew.")

    new_contract = create_contract(
        db,
        company_id=prior_contract.company_id,
        customer_id=prior_contract.customer_id,
        contracted_hours=contracted_hours,
        contract_value_sgd=contract_value_sgd,
        start_date=start_date,
        actor_user_id=actor_user_id,
        renewed_from_contract_id=prior_contract.id,
    )

    if prior_contract.status != ContractStatus.EXPIRED:
        expire_contract(db, prior_contract, actor_user_id=actor_user_id)

    prior_contract.status = ContractStatus.RENEWED
    db.flush()

    audit.record(
        db,
        entity_type="contract",
        entity_id=new_contract.id,
        action="renewed_from",
        actor_user_id=actor_user_id,
        details=f"prior_contract_id={prior_contract.id}, backdated={eligibility.eligible_for_backdating}",
    )
    return new_contract
