"""
Chart of Accounts maintenance.

The seeded chart is a conventional Singapore SME starting point
(confirmed approach, 2026-09-10) -- this API is how Dennis adjusts it to
how Webmaster actually wants its books structured.
"""
import uuid

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.models.accounting import Account, AccountType
from app.core.database import get_db
from app.models.core import User
from app.models.groups import AccessLevel
from app.schemas.schemas import AccountCreate, AccountOut, AccountUpdate
from app.services import audit
from app.services.authority import require_module_access

router = APIRouter(prefix="/api/accounts", tags=["chart-of-accounts"])
MODULE = "finance_accounting"


@router.get("", response_model=list[AccountOut])
def list_accounts(
    include_inactive: bool = False,
    account_type: AccountType | None = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_module_access(MODULE, AccessLevel.VIEW)),
):
    query = db.query(Account).filter(Account.company_id == current_user.company_id)
    if not include_inactive:
        query = query.filter(Account.is_active)
    if account_type:
        query = query.filter(Account.account_type == account_type)
    return query.order_by(Account.code).all()


@router.post("", response_model=AccountOut)
def create_account(
    payload: AccountCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_module_access(MODULE, AccessLevel.EDIT)),
):
    existing = (
        db.query(Account)
        .filter(Account.company_id == current_user.company_id, Account.code == payload.code)
        .first()
    )
    if existing:
        raise HTTPException(
            status_code=409, detail=f"Account code {payload.code} already exists."
        )

    account = Account(
        company_id=current_user.company_id,
        code=payload.code,
        name=payload.name,
        account_type=payload.account_type,
        description=payload.description,
    )
    db.add(account)
    db.flush()
    audit.record(
        db,
        entity_type="account",
        entity_id=account.id,
        action="created",
        actor_user_id=current_user.id,
        details=f"{payload.code} {payload.name}",
        new_value={
            "code": payload.code,
            "name": payload.name,
            "account_type": payload.account_type.value,
        },
    )
    db.commit()
    db.refresh(account)
    return account


@router.patch("/{account_id}", response_model=AccountOut)
def update_account(
    account_id: uuid.UUID,
    payload: AccountUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_module_access(MODULE, AccessLevel.EDIT)),
):
    account = db.get(Account, account_id)
    if not account or account.company_id != current_user.company_id:
        raise HTTPException(status_code=404, detail="Account not found")

    fields = payload.model_dump(exclude_unset=True)
    old_value: dict[str, object] = {}
    new_value: dict[str, object] = {}
    for field in ("code", "name", "account_type", "description", "is_active"):
        if field not in fields:
            continue
        old = getattr(account, field)
        new = fields[field]
        if old == new:
            continue
        old_value[field] = old.value if hasattr(old, "value") else old
        new_value[field] = new.value if hasattr(new, "value") else new
        setattr(account, field, new)

    audit.record(
        db,
        entity_type="account",
        entity_id=account.id,
        action="updated",
        actor_user_id=current_user.id,
        details=f"{account.code} {account.name}",
        old_value=old_value or None,
        new_value=new_value or None,
    )
    db.commit()
    db.refresh(account)
    return account
