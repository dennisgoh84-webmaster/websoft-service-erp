"""
Accounting Periods and Year-End Closing. See app/models/periods.py and
app/services/periods.py for the mechanics and the two pragmatic,
explicitly-flagged defaults this implements.
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


@router.post("/{period_id}/close", response_model=AccountingPeriodOut)
def close_period_endpoint(
    period_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_module_access(MODULE, AccessLevel.FULL)),
):
    period = db.get(AccountingPeriod, period_id)
    if not period or period.company_id != current_user.company_id:
        raise HTTPException(status_code=404, detail="Period not found")
    if period.status == PeriodStatus.CLOSED:
        raise HTTPException(status_code=422, detail="That period is already closed.")

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
    # Reopening a closed period is a bigger deal than closing one -- it
    # lets past-dated postings resume -- so it's owner-only, mirroring
    # the "owner approves the risky reversal" pattern used elsewhere
    # (write-off threshold, excess-usage decisions).
    current_user: User = Depends(require_module_access(MODULE, AccessLevel.FULL)),
):
    if current_user.role != UserRole.OWNER:
        raise HTTPException(status_code=403, detail="Only the owner can reopen a closed accounting period.")
    period = db.get(AccountingPeriod, period_id)
    if not period or period.company_id != current_user.company_id:
        raise HTTPException(status_code=404, detail="Period not found")
    if period.status == PeriodStatus.OPEN:
        raise HTTPException(status_code=422, detail="That period is already open.")

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
    chosen Equity account. Owner-only -- this has real bookkeeping
    consequences (confirmed 2026-09-11), unlike closing a single period."""
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
