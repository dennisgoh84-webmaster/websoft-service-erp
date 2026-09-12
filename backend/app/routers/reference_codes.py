"""
Reference Monitor maintenance -- GL sub-codes under one Chart of
Accounts row (see app/models/reference_codes.py's module docstring).
Lives under the same finance_accounting module authority as Chart of
Accounts, since it is a direct extension of it.
"""
import uuid

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.models.accounting import Account
from app.models.core import User
from app.models.groups import AccessLevel
from app.models.reference_codes import ReferenceCode
from app.schemas.schemas import ReferenceCodeCreate, ReferenceCodeOut, ReferenceCodeUpdate
from app.services import audit, exports
from app.services.authority import require_module_access

router = APIRouter(prefix="/api/reference-codes", tags=["reference-monitor"])
MODULE = "finance_accounting"

REFERENCE_CODE_EXPORT_FIELDS = ["code", "name", "account_code", "account_name", "is_active"]


def _filter_reference_codes(
    db: Session,
    company_id: uuid.UUID,
    include_inactive: bool,
    account_id: uuid.UUID | None,
) -> list[ReferenceCode]:
    query = db.query(ReferenceCode).filter(ReferenceCode.company_id == company_id)
    if not include_inactive:
        query = query.filter(ReferenceCode.is_active)
    if account_id:
        query = query.filter(ReferenceCode.account_id == account_id)
    return query.order_by(ReferenceCode.code).all()


def _out(rc: ReferenceCode) -> ReferenceCodeOut:
    return ReferenceCodeOut(
        id=rc.id,
        account_id=rc.account_id,
        account_code=rc.account.code if rc.account else None,
        account_name=rc.account.name if rc.account else None,
        code=rc.code,
        name=rc.name,
        is_active=rc.is_active,
        created_at=rc.created_at,
    )


@router.get("", response_model=list[ReferenceCodeOut])
def list_reference_codes(
    include_inactive: bool = False,
    account_id: uuid.UUID | None = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_module_access(MODULE, AccessLevel.VIEW)),
):
    rows = _filter_reference_codes(db, current_user.company_id, include_inactive, account_id)
    return [_out(r) for r in rows]


def _reference_codes_for_export(
    db: Session, company_id: uuid.UUID, include_inactive: bool, account_id: uuid.UUID | None
) -> list[dict]:
    rows = _filter_reference_codes(db, company_id, include_inactive, account_id)
    return [
        {
            "code": r.code,
            "name": r.name,
            "account_code": r.account.code if r.account else "",
            "account_name": r.account.name if r.account else "",
            "is_active": r.is_active,
        }
        for r in rows
    ]


@router.get("/export.csv")
def export_reference_codes_csv(
    include_inactive: bool = False,
    account_id: uuid.UUID | None = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_module_access(MODULE, AccessLevel.VIEW)),
):
    rows = _reference_codes_for_export(db, current_user.company_id, include_inactive, account_id)
    csv_text = exports.rows_to_csv(REFERENCE_CODE_EXPORT_FIELDS, rows)
    return StreamingResponse(
        iter([csv_text]),
        media_type="text/csv",
        headers={"Content-Disposition": "attachment; filename=reference-codes.csv"},
    )


@router.get("/export.xlsx")
def export_reference_codes_excel(
    include_inactive: bool = False,
    account_id: uuid.UUID | None = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_module_access(MODULE, AccessLevel.VIEW)),
):
    rows = _reference_codes_for_export(db, current_user.company_id, include_inactive, account_id)
    data = exports.rows_to_excel(REFERENCE_CODE_EXPORT_FIELDS, rows, sheet_name="Reference Codes")
    return StreamingResponse(
        iter([data]),
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": "attachment; filename=reference-codes.xlsx"},
    )


@router.post("", response_model=ReferenceCodeOut)
def create_reference_code(
    payload: ReferenceCodeCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_module_access(MODULE, AccessLevel.EDIT)),
):
    account = db.get(Account, payload.account_id)
    if not account or account.company_id != current_user.company_id:
        raise HTTPException(status_code=404, detail="Account not found")

    existing = (
        db.query(ReferenceCode)
        .filter(ReferenceCode.company_id == current_user.company_id, ReferenceCode.code == payload.code)
        .first()
    )
    if existing:
        raise HTTPException(status_code=409, detail=f"Reference code {payload.code} already exists.")

    rc = ReferenceCode(
        company_id=current_user.company_id,
        account_id=payload.account_id,
        code=payload.code,
        name=payload.name,
    )
    db.add(rc)
    db.flush()
    audit.record(
        db,
        entity_type="reference_code",
        entity_id=rc.id,
        action="created",
        actor_user_id=current_user.id,
        details=f"{payload.code} {payload.name} -> {account.code}",
        new_value={"code": payload.code, "name": payload.name, "account_code": account.code},
    )
    db.commit()
    db.refresh(rc)
    return _out(rc)


@router.patch("/{reference_code_id}", response_model=ReferenceCodeOut)
def update_reference_code(
    reference_code_id: uuid.UUID,
    payload: ReferenceCodeUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_module_access(MODULE, AccessLevel.EDIT)),
):
    rc = db.get(ReferenceCode, reference_code_id)
    if not rc or rc.company_id != current_user.company_id:
        raise HTTPException(status_code=404, detail="Reference code not found")

    fields = payload.model_dump(exclude_unset=True)
    if "account_id" in fields and fields["account_id"] is not None:
        account = db.get(Account, fields["account_id"])
        if not account or account.company_id != current_user.company_id:
            raise HTTPException(status_code=404, detail="Account not found")

    old_value: dict[str, object] = {}
    new_value: dict[str, object] = {}
    for field in ("account_id", "code", "name", "is_active"):
        if field not in fields:
            continue
        old = getattr(rc, field)
        new = fields[field]
        if old == new:
            continue
        old_value[field] = str(old)
        new_value[field] = str(new)
        setattr(rc, field, new)

    audit.record(
        db,
        entity_type="reference_code",
        entity_id=rc.id,
        action="updated",
        actor_user_id=current_user.id,
        details=f"{rc.code} {rc.name}",
        old_value=old_value or None,
        new_value=new_value or None,
    )
    db.commit()
    db.refresh(rc)
    return _out(rc)
