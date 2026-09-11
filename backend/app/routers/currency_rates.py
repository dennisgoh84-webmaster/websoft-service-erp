"""Currency Rate Table -- setup data only; see app/models/treasury.py
for why nothing in the app converts an amount using these rates yet."""
import uuid

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.models.core import User
from app.models.groups import AccessLevel
from app.models.treasury import CurrencyRate
from app.schemas.schemas import CurrencyRateCreate, CurrencyRateOut, CurrencyRateUpdate
from app.services import audit
from app.services.authority import require_module_access

router = APIRouter(prefix="/api/currency-rates", tags=["currency-rates"])
MODULE = "finance_accounting"


@router.get("", response_model=list[CurrencyRateOut])
def list_currency_rates(
    currency_code: str | None = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_module_access(MODULE, AccessLevel.VIEW)),
):
    query = db.query(CurrencyRate).filter(CurrencyRate.company_id == current_user.company_id)
    if currency_code:
        query = query.filter(CurrencyRate.currency_code == currency_code.upper())
    return query.order_by(CurrencyRate.currency_code, CurrencyRate.effective_date.desc()).all()


@router.post("", response_model=CurrencyRateOut)
def create_currency_rate(
    payload: CurrencyRateCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_module_access(MODULE, AccessLevel.EDIT)),
):
    rate = CurrencyRate(
        company_id=current_user.company_id,
        currency_code=payload.currency_code.upper(),
        rate_to_base=payload.rate_to_base,
        effective_date=payload.effective_date,
    )
    db.add(rate)
    db.flush()
    audit.record(
        db,
        entity_type="currency_rate",
        entity_id=rate.id,
        action="created",
        actor_user_id=current_user.id,
        details=f"{rate.currency_code} @ {rate.rate_to_base} as at {rate.effective_date}",
        new_value={"currency_code": rate.currency_code, "rate_to_base": str(rate.rate_to_base)},
    )
    db.commit()
    db.refresh(rate)
    return rate


@router.patch("/{rate_id}", response_model=CurrencyRateOut)
def update_currency_rate(
    rate_id: uuid.UUID,
    payload: CurrencyRateUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_module_access(MODULE, AccessLevel.EDIT)),
):
    rate = db.get(CurrencyRate, rate_id)
    if not rate or rate.company_id != current_user.company_id:
        raise HTTPException(status_code=404, detail="Currency rate not found")

    fields = payload.model_dump(exclude_unset=True)
    old_value: dict[str, object] = {}
    new_value: dict[str, object] = {}
    for field in ("rate_to_base", "is_active"):
        if field not in fields:
            continue
        old = getattr(rate, field)
        new = fields[field]
        if old == new:
            continue
        old_value[field] = str(old)
        new_value[field] = str(new)
        setattr(rate, field, new)

    audit.record(
        db,
        entity_type="currency_rate",
        entity_id=rate.id,
        action="updated",
        actor_user_id=current_user.id,
        details=f"{rate.currency_code} as at {rate.effective_date}",
        old_value=old_value or None,
        new_value=new_value or None,
    )
    db.commit()
    db.refresh(rate)
    return rate
