"""
Accounting Periods and Year-End Closing.

Updated 2026-09-12: replaced binary close/reopen with granular
per-document-type, per-operation lock matrix. Close All / Open All
are convenience actions that set every lock at once; individual
locks can be toggled one cell at a time from the frontend grid.

See app/models/periods.py for the lock matrix and
app/services/periods.py for the enforcement and year-end mechanics.
"""
import uuid

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.models.core import User, UserRole
from app.models.groups import AccessLevel
from app.models.periods import AccountingPeriod, FiscalYearClosure, PeriodStatus
from app.schemas.schemas import (
    AccountingPeriodCreate,
    AccountingPeriodOut,
    FiscalYearClosureOut,
    PeriodLockToggleRequest,
    YearEndClosingRequest,
)
from app.services import audit
from app.services import periods as periods_svc
from app.services.authority import require_module_access

router = APIRouter(prefix="/api/accounting-periods", tags=["accounting-periods"])
MODULE = "finance_accounting"


@router.get("", response_model=list[AccountingPeriodOut])
def list_periods(
    fiscal_year: int | None = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_module_access(MODULE, AccessLevel.VIEW)),
):
    query = db.query(AccountingPeriod).filter(AccountingPeriod.company_id == current_user.company_id)
    if fiscal_year:
        query = query.filter(AccountingPeriod.fiscal_year == fiscal_year)
    return query.order_by(AccountingPeriod.period_start).all()


@router.post("", response_model=AccountingPeriodOut)
def create_period(
    payload: AccountingPeriodCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_module_access(MODULE, AccessLevel.FULL)),
):
    if payload.period_end < payload.period_start:
        raise HTTPException(status_code=422, detail="period_end cannot be before period_start.")
    overlap = (
        db.query(AccountingPeriod)
        .filter(
            AccountingPeriod.company_id == current_user.company_id,
            AccountingPeriod.period_start <= payload.period_end,
            AccountingPeriod.period_end >= payload.period_start,
        )
        .first()
    )
    if overlap:
        raise HTTPException(
            status_code=409, detail=f'Overlaps existing period "{overlap.name}" ({overlap.period_start} to {overlap.period_end}).'
        )

    period = AccountingPeriod(company_id=current_user.company_id, **payload.model_dump())
    db.add(period)
    db.flush()
    periods_svc.seed_locks_for_period(db, period, locked=False)
    audit.record(
        db,
        entity_type="accounting_period",
        entity_id=period.id,
        action="created",
        actor_user_id=current_user.id,
        details=f"{period.name} ({period.period_start} to {period.period_end})",
        new_value={"name": period.name, "period_start": str(period.period_start), "period_end": str(period.period_end)},
    )
    db.commit()
    db.refresh(period)
    return period


# ---- Lock toggle (single cell) ----------------------------------------


@router.post("/{period_id}/toggle-lock", response_model=AccountingPeriodOut)
def toggle_lock_endpoint(
    period_id: uuid.UUID,
    payload: PeriodLockToggleRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_module_access(MODULE, AccessLevel.FULL)),
):
    """Lock or unlock one doc-type × operation cell."""
    period = db.get(AccountingPeriod, period_id)
    if not period or period.company_id != current_user.company_id:
        raise HTTPException(status_code=404, detail="Period not found")
    try:
        periods_svc.toggle_lock(
            db,
            period,
            payload.doc_type,
            payload.operation,
            locked=payload.locked,
            actor_user_id=current_user.id,
        )
    except ValueError as e:
        raise HTTPException(status_code=422, detail=str(e))
    action = "locked" if payload.locked else "unlocked"
    audit.record(
        db,
        entity_type="accounting_period",
        entity_id=period.id,
        action=f"lock_{action}",
        actor_user_id=current_user.id,
        details=f"{payload.doc_type.value}/{payload.operation.value} {action} in {period.name}",
        new_value={"doc_type": payload.doc_type.value, "operation": payload.operation.value, "is_locked": payload.locked},
    )
    db.commit()
    db.refresh(period)
    return period


# ---- Close All / Open All ----------------------------------------------


@router.post("/{period_id}/close", response_model=AccountingPeriodOut)
def close_period_endpoint(
    period_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_module_access(MODULE, AccessLevel.FULL)),
):
    """Lock every operation for every doc type ("Close All")."""
    period = db.get(AccountingPeriod, period_id)
    if not period or period.company_id != current_user.company_id:
        raise HTTPException(status_code=404, detail="Period not found")
    if period.status == PeriodStatus.CLOSED:
        raise HTTPException(status_code=422, detail="That period is already fully closed.")

    periods_svc.close_period(db, period, actor_user_id=current_user.id)
    audit.record(
        db,
        entity_type="accounting_period",
        entity_id=period.id,
        action="closed",
        actor_user_id=current_user.id,
        details=period.name,
        old_value={"status": "open"},
        new_value={"status": "closed"},
    )
    db.commit()
    db.refresh(period)
    return period


@router.post("/{period_id}/reopen", response_model=AccountingPeriodOut)
def reopen_period_endpoint(
    period_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_module_access(MODULE, AccessLevel.FULL)),
):
    """Unlock every operation for every doc type ("Open All"). Owner-only."""
    if current_user.role != UserRole.OWNER:
        raise HTTPException(status_code=403, detail="Only the owner can reopen a closed accounting period.")
    period = db.get(AccountingPeriod, period_id)
    if not period or period.company_id != current_user.company_id:
        raise HTTPException(status_code=404, detail="Period not found")
    if period.status == PeriodStatus.OPEN:
        # Check if any individual lock is set (partial state)
        any_locked = any(lk.is_locked for lk in period.locks)
        if not any_locked:
            raise HTTPException(status_code=422, detail="That period is already fully open.")

    periods_svc.reopen_period(db, period)
    audit.record(
        db,
        entity_type="accounting_period",
        entity_id=period.id,
        action="reopened",
        actor_user_id=current_user.id,
        details=period.name,
        old_value={"status": "closed"},
        new_value={"status": "open"},
    )
    db.commit()
    db.refresh(period)
    return period


# ---- Year-End Closing ---------------------------------------------------


@router.get("/closures", response_model=list[FiscalYearClosureOut])
def list_fiscal_year_closures(
    db: Session = Depends(get_db),
    current_user: User = Depends(require_module_access(MODULE, AccessLevel.VIEW)),
):
    return (
        db.query(FiscalYearClosure)
        .filter(FiscalYearClosure.company_id == current_user.company_id)
        .order_by(FiscalYearClosure.fiscal_year.desc())
        .all()
    )


@router.post("/close-fiscal-year", response_model=FiscalYearClosureOut)
def close_fiscal_year_endpoint(
    payload: YearEndClosingRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_module_access(MODULE, AccessLevel.FULL)),
):
    """Year-End Closing: posts one closing journal entry moving every
    Revenue/Expense account's movement for the fiscal year into the
    chosen Equity account. Owner-only."""
    if current_user.role != UserRole.OWNER:
        raise HTTPException(status_code=403, detail="Only the owner can perform Year-End Closing.")

    try:
        entry = periods_svc.close_fiscal_year(
            db,
            company_id=current_user.company_id,
            fiscal_year=payload.fiscal_year,
            retained_earnings_account_id=payload.retained_earnings_account_id,
            actor_user_id=current_user.id,
        )
    except periods_svc.YearEndClosingError as e:
        raise HTTPException(status_code=422, detail=str(e))

    closure = (
        db.query(FiscalYearClosure)
        .filter(
            FiscalYearClosure.company_id == current_user.company_id,
            FiscalYearClosure.fiscal_year == payload.fiscal_year,
        )
        .first()
    )
    audit.record(
        db,
        entity_type="fiscal_year_closure",
        entity_id=closure.id,
        action="closed",
        actor_user_id=current_user.id,
        details=f"FY{payload.fiscal_year} closed via voucher {entry.voucher_number}",
        new_value={"fiscal_year": payload.fiscal_year, "voucher_number": entry.voucher_number},
    )
    db.commit()
    db.refresh(closure)
    return closure
