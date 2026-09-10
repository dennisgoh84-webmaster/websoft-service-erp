"""
General Ledger -- Journal Vouchers and the trial balance.

A Journal Voucher is the manual double entry: the person raising it
chooses the debit and credit accounts themselves. That is deliberate --
the posting rules for automatic entries (which account a sales invoice
credits, how GST output tax is posted) are still undecided (open item
4b.2), so nothing here assumes them on Dennis's behalf.
"""
import uuid
from datetime import date

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session, selectinload

from app.core.database import get_db
from app.models.accounting import JournalEntry, JournalStatus, VoucherType
from app.models.core import User
from app.models.groups import AccessLevel
from app.schemas.schemas import (
    JournalEntryCreate,
    JournalEntryOut,
    ReverseRequest,
    TrialBalance,
    TrialBalanceRow,
)
from app.services import audit
from app.services import ledger as ledger_svc
from app.services.authority import require_module_access

router = APIRouter(prefix="/api/ledger", tags=["general-ledger"])
MODULE = "finance_accounting"


def _entry_or_404(db: Session, entry_id: uuid.UUID, company_id: uuid.UUID) -> JournalEntry:
    entry = (
        db.query(JournalEntry)
        .options(selectinload(JournalEntry.lines))
        .filter(JournalEntry.id == entry_id, JournalEntry.company_id == company_id)
        .first()
    )
    if not entry:
        raise HTTPException(status_code=404, detail="Voucher not found")
    return entry


@router.get("/vouchers", response_model=list[JournalEntryOut])
def list_vouchers(
    voucher_type: VoucherType | None = None,
    status: JournalStatus | None = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_module_access(MODULE, AccessLevel.VIEW)),
):
    query = (
        db.query(JournalEntry)
        .options(selectinload(JournalEntry.lines))
        .filter(JournalEntry.company_id == current_user.company_id)
    )
    if voucher_type:
        query = query.filter(JournalEntry.voucher_type == voucher_type)
    if status:
        query = query.filter(JournalEntry.status == status)
    entries = query.order_by(JournalEntry.entry_date.desc(), JournalEntry.created_at.desc()).all()
    return [JournalEntryOut.from_model(e) for e in entries]


@router.get("/vouchers/{entry_id}", response_model=JournalEntryOut)
def get_voucher(
    entry_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_module_access(MODULE, AccessLevel.VIEW)),
):
    return JournalEntryOut.from_model(_entry_or_404(db, entry_id, current_user.company_id))


@router.post("/vouchers", response_model=JournalEntryOut)
def create_journal_voucher(
    payload: JournalEntryCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_module_access(MODULE, AccessLevel.EDIT)),
):
    """Raise a Journal Voucher. Created as a draft unless `post` is set;
    either way it must balance before it can be posted."""
    try:
        entry = ledger_svc.create_journal_entry(
            db,
            company_id=current_user.company_id,
            entry_date=payload.entry_date,
            narration=payload.narration,
            voucher_type=VoucherType.JOURNAL,
            created_by_user_id=current_user.id,
            lines=[line.model_dump() for line in payload.lines],
        )
        if payload.post:
            ledger_svc.post_entry(db, entry, actor_user_id=current_user.id)
    except ledger_svc.LedgerRuleViolation as e:
        raise HTTPException(status_code=422, detail=str(e))

    audit.record(
        db,
        entity_type="journal_entry",
        entity_id=entry.id,
        action="posted" if payload.post else "created",
        actor_user_id=current_user.id,
        details=f"{entry.voucher_number}: {payload.narration}",
        new_value={
            "voucher_number": entry.voucher_number,
            "debit_sgd": str(entry.total_debit),
            "credit_sgd": str(entry.total_credit),
            "status": entry.status.value,
        },
    )
    db.commit()
    db.refresh(entry)
    return JournalEntryOut.from_model(entry)


@router.post("/vouchers/{entry_id}/post", response_model=JournalEntryOut)
def post_voucher(
    entry_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_module_access(MODULE, AccessLevel.FULL)),
):
    """Post a draft to the ledger. Refuses anything that doesn't balance."""
    entry = _entry_or_404(db, entry_id, current_user.company_id)
    try:
        ledger_svc.post_entry(db, entry, actor_user_id=current_user.id)
    except ledger_svc.LedgerRuleViolation as e:
        raise HTTPException(status_code=422, detail=str(e))

    audit.record(
        db,
        entity_type="journal_entry",
        entity_id=entry.id,
        action="posted",
        actor_user_id=current_user.id,
        details=f"{entry.voucher_number}: SGD {entry.total_debit}",
        old_value={"status": "draft"},
        new_value={"status": "posted"},
    )
    db.commit()
    db.refresh(entry)
    return JournalEntryOut.from_model(entry)


@router.post("/vouchers/{entry_id}/reverse", response_model=JournalEntryOut)
def reverse_voucher(
    entry_id: uuid.UUID,
    payload: ReverseRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_module_access(MODULE, AccessLevel.FULL)),
):
    """Reverse a posted voucher. The original stays exactly as it was --
    a mirror entry is written instead, so both the mistake and its
    correction remain on record."""
    entry = _entry_or_404(db, entry_id, current_user.company_id)
    try:
        reversal = ledger_svc.reverse_entry(
            db, entry, actor_user_id=current_user.id, reason=payload.reason
        )
    except ledger_svc.LedgerRuleViolation as e:
        raise HTTPException(status_code=422, detail=str(e))

    audit.record(
        db,
        entity_type="journal_entry",
        entity_id=entry.id,
        action="reversed",
        actor_user_id=current_user.id,
        reason=payload.reason,
        details=f"{entry.voucher_number} reversed by {reversal.voucher_number}",
        old_value={"status": "posted"},
        new_value={"status": "reversed", "reversal_voucher": reversal.voucher_number},
    )
    db.commit()
    db.refresh(reversal)
    return JournalEntryOut.from_model(reversal)


@router.get("/trial-balance", response_model=TrialBalance)
def trial_balance(
    as_at: date | None = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_module_access(MODULE, AccessLevel.VIEW)),
):
    """Posted debits and credits per account. Draft and reversed vouchers
    are excluded -- only posted entries are part of the ledger."""
    rows = ledger_svc.account_balances(db, current_user.company_id, as_at)
    out = [
        TrialBalanceRow(
            account_id=r["account_id"],
            code=r["code"],
            name=r["name"],
            account_type=r["account_type"],
            debit_sgd=float(r["debit_sgd"]),
            credit_sgd=float(r["credit_sgd"]),
            balance_sgd=float(r["balance_sgd"]),
        )
        for r in rows
    ]
    total_debit = sum(r.debit_sgd for r in out)
    total_credit = sum(r.credit_sgd for r in out)
    return TrialBalance(
        as_at=as_at,
        rows=out,
        total_debit=total_debit,
        total_credit=total_credit,
        # A trial balance that doesn't balance means something is wrong
        # with the ledger itself, so it is surfaced rather than hidden.
        is_balanced=round(total_debit, 2) == round(total_credit, 2),
    )
