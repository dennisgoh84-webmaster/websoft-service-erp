"""Bank Master File -- the company's own bank accounts. Setup data
only; see app/models/treasury.py for what's deliberately not wired up
yet (no Receipt/Payment/GL posting reads from this)."""
import uuid

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.models.accounting import Account
from app.models.core import User
from app.models.groups import AccessLevel
from app.models.treasury import BankAccount
from app.schemas.schemas import BankAccountCreate, BankAccountOut, BankAccountUpdate
from app.services import audit, exports
from app.services.authority import require_module_access

router = APIRouter(prefix="/api/bank-accounts", tags=["bank-accounts"])
MODULE = "finance_accounting"

BANK_ACCOUNT_EXPORT_FIELDS = [
    "bank_name", "account_name", "account_number", "branch", "swift_code",
    "currency_code", "gl_account_code", "is_active",
]


def _filter_bank_accounts(db: Session, company_id: uuid.UUID, include_inactive: bool) -> list[BankAccount]:
    query = db.query(BankAccount).filter(BankAccount.company_id == company_id)
    if not include_inactive:
        query = query.filter(BankAccount.is_active)
    return query.order_by(BankAccount.bank_name, BankAccount.account_name).all()


@router.get("", response_model=list[BankAccountOut])
def list_bank_accounts(
    include_inactive: bool = False,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_module_access(MODULE, AccessLevel.VIEW)),
):
    return _filter_bank_accounts(db, current_user.company_id, include_inactive)


def _row(b: BankAccount, gl_codes: dict) -> dict:
    return {
        "bank_name": b.bank_name,
        "account_name": b.account_name,
        "account_number": b.account_number,
        "branch": b.branch or "",
        "swift_code": b.swift_code or "",
        "currency_code": b.currency_code,
        "gl_account_code": gl_codes.get(b.gl_account_id, ""),
        "is_active": b.is_active,
    }


def _bank_accounts_for_export(db: Session, company_id: uuid.UUID, include_inactive: bool) -> list[dict]:
    accounts = _filter_bank_accounts(db, company_id, include_inactive)
    gl_codes = {a.id: a.code for a in db.query(Account).filter(Account.company_id == company_id)}
    return [_row(b, gl_codes) for b in accounts]


@router.get("/export.csv")
def export_bank_accounts_csv(
    include_inactive: bool = False,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_module_access(MODULE, AccessLevel.VIEW)),
):
    rows = _bank_accounts_for_export(db, current_user.company_id, include_inactive)
    csv_text = exports.rows_to_csv(BANK_ACCOUNT_EXPORT_FIELDS, rows)
    return StreamingResponse(
        iter([csv_text]),
        media_type="text/csv",
        headers={"Content-Disposition": "attachment; filename=bank-accounts.csv"},
    )


@router.get("/export.xlsx")
def export_bank_accounts_excel(
    include_inactive: bool = False,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_module_access(MODULE, AccessLevel.VIEW)),
):
    rows = _bank_accounts_for_export(db, current_user.company_id, include_inactive)
    data = exports.rows_to_excel(BANK_ACCOUNT_EXPORT_FIELDS, rows, sheet_name="Bank Accounts")
    return StreamingResponse(
        iter([data]),
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": "attachment; filename=bank-accounts.xlsx"},
    )


@router.post("", response_model=BankAccountOut)
def create_bank_account(
    payload: BankAccountCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_module_access(MODULE, AccessLevel.EDIT)),
):
    if payload.gl_account_id:
        gl_account = db.get(Account, payload.gl_account_id)
        if not gl_account or gl_account.company_id != current_user.company_id:
            raise HTTPException(status_code=404, detail="Unknown GL account")

    bank_account = BankAccount(company_id=current_user.company_id, **payload.model_dump())
    db.add(bank_account)
    db.flush()
    audit.record(
        db,
        entity_type="bank_account",
        entity_id=bank_account.id,
        action="created",
        actor_user_id=current_user.id,
        details=f"{bank_account.bank_name} {bank_account.account_number}",
        new_value={"bank_name": bank_account.bank_name, "account_number": bank_account.account_number},
    )
    db.commit()
    db.refresh(bank_account)
    return bank_account


@router.patch("/{bank_account_id}", response_model=BankAccountOut)
def update_bank_account(
    bank_account_id: uuid.UUID,
    payload: BankAccountUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_module_access(MODULE, AccessLevel.EDIT)),
):
    bank_account = db.get(BankAccount, bank_account_id)
    if not bank_account or bank_account.company_id != current_user.company_id:
        raise HTTPException(status_code=404, detail="Bank account not found")

    fields = payload.model_dump(exclude_unset=True)
    if "gl_account_id" in fields and fields["gl_account_id"]:
        gl_account = db.get(Account, fields["gl_account_id"])
        if not gl_account or gl_account.company_id != current_user.company_id:
            raise HTTPException(status_code=404, detail="Unknown GL account")

    old_value: dict[str, object] = {}
    new_value: dict[str, object] = {}
    for field in (
        "bank_name", "account_name", "account_number", "branch", "swift_code",
        "currency_code", "gl_account_id", "is_active",
    ):
        if field not in fields:
            continue
        old = getattr(bank_account, field)
        new = fields[field]
        if old == new:
            continue
        old_value[field] = str(old) if old is not None else None
        new_value[field] = str(new) if new is not None else None
        setattr(bank_account, field, new)

    audit.record(
        db,
        entity_type="bank_account",
        entity_id=bank_account.id,
        action="updated",
        actor_user_id=current_user.id,
        details=f"{bank_account.bank_name} {bank_account.account_number}",
        old_value=old_value or None,
        new_value=new_value or None,
    )
    db.commit()
    db.refresh(bank_account)
    return bank_account
