"""Tax Type maintenance -- CRUD over the TaxCode table used for GST
(see app/models/tax.py). Rates are data, not hard-coded, so a change
(Singapore has moved its GST rate twice in recent years) is an edit
here rather than a code change; historical invoices keep the rate they
were actually raised at regardless of later edits (Invoice.gst_rate)."""
import uuid

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.models.core import User
from app.models.groups import AccessLevel
from app.models.tax import TaxCode
from app.schemas.schemas import TaxCodeCreate, TaxCodeOut, TaxCodeUpdate
from app.services import audit, exports
from app.services.authority import require_module_access

router = APIRouter(prefix="/api/tax-codes", tags=["tax-codes"])
MODULE = "finance_accounting"

TAX_CODE_EXPORT_FIELDS = ["code", "name", "rate_percent", "is_active"]


def _filter_tax_codes(db: Session, company_id: uuid.UUID, include_inactive: bool) -> list[TaxCode]:
    query = db.query(TaxCode).filter(TaxCode.company_id == company_id)
    if not include_inactive:
        query = query.filter(TaxCode.is_active)
    return query.order_by(TaxCode.code).all()


@router.get("", response_model=list[TaxCodeOut])
def list_tax_codes(
    include_inactive: bool = False,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_module_access(MODULE, AccessLevel.VIEW)),
):
    return _filter_tax_codes(db, current_user.company_id, include_inactive)


@router.get("/export.csv")
def export_tax_codes_csv(
    include_inactive: bool = False,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_module_access(MODULE, AccessLevel.VIEW)),
):
    rows = [
        {"code": t.code, "name": t.name, "rate_percent": str(t.rate_percent), "is_active": t.is_active}
        for t in _filter_tax_codes(db, current_user.company_id, include_inactive)
    ]
    csv_text = exports.rows_to_csv(TAX_CODE_EXPORT_FIELDS, rows)
    return StreamingResponse(
        iter([csv_text]),
        media_type="text/csv",
        headers={"Content-Disposition": "attachment; filename=tax-types.csv"},
    )


@router.get("/export.xlsx")
def export_tax_codes_excel(
    include_inactive: bool = False,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_module_access(MODULE, AccessLevel.VIEW)),
):
    rows = [
        {"code": t.code, "name": t.name, "rate_percent": str(t.rate_percent), "is_active": t.is_active}
        for t in _filter_tax_codes(db, current_user.company_id, include_inactive)
    ]
    data = exports.rows_to_excel(TAX_CODE_EXPORT_FIELDS, rows, sheet_name="Tax Types")
    return StreamingResponse(
        iter([data]),
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": "attachment; filename=tax-types.xlsx"},
    )


@router.post("", response_model=TaxCodeOut)
def create_tax_code(
    payload: TaxCodeCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_module_access(MODULE, AccessLevel.EDIT)),
):
    existing = (
        db.query(TaxCode)
        .filter(TaxCode.company_id == current_user.company_id, TaxCode.code == payload.code)
        .first()
    )
    if existing:
        raise HTTPException(status_code=409, detail=f"Tax code {payload.code} already exists.")

    tax_code = TaxCode(company_id=current_user.company_id, **payload.model_dump())
    db.add(tax_code)
    db.flush()
    audit.record(
        db,
        entity_type="tax_code",
        entity_id=tax_code.id,
        action="created",
        actor_user_id=current_user.id,
        details=f"{tax_code.code} {tax_code.name} @ {tax_code.rate_percent}%",
        new_value={"code": tax_code.code, "name": tax_code.name, "rate_percent": str(tax_code.rate_percent)},
    )
    db.commit()
    db.refresh(tax_code)
    return tax_code


@router.patch("/{tax_code_id}", response_model=TaxCodeOut)
def update_tax_code(
    tax_code_id: uuid.UUID,
    payload: TaxCodeUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_module_access(MODULE, AccessLevel.EDIT)),
):
    tax_code = db.get(TaxCode, tax_code_id)
    if not tax_code or tax_code.company_id != current_user.company_id:
        raise HTTPException(status_code=404, detail="Tax code not found")

    fields = payload.model_dump(exclude_unset=True)
    old_value: dict[str, object] = {}
    new_value: dict[str, object] = {}
    for field in ("code", "name", "rate_percent", "is_active"):
        if field not in fields:
            continue
        old = getattr(tax_code, field)
        new = fields[field]
        if old == new:
            continue
        old_value[field] = str(old)
        new_value[field] = str(new)
        setattr(tax_code, field, new)

    audit.record(
        db,
        entity_type="tax_code",
        entity_id=tax_code.id,
        action="updated",
        actor_user_id=current_user.id,
        details=f"{tax_code.code} {tax_code.name}",
        old_value=old_value or None,
        new_value=new_value or None,
    )
    db.commit()
    db.refresh(tax_code)
    return tax_code
