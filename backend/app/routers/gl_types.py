"""GL Types -- a finer classification within the 5 AccountType classes
that an Account can optionally carry (see app/models/accounting.py)."""
import uuid

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.models.accounting import GLType
from app.models.core import User
from app.models.groups import AccessLevel
from app.schemas.schemas import GLTypeCreate, GLTypeOut, GLTypeUpdate
from app.services import audit
from app.services.authority import require_module_access

router = APIRouter(prefix="/api/gl-types", tags=["gl-types"])
MODULE = "finance_accounting"


@router.get("", response_model=list[GLTypeOut])
def list_gl_types(
    include_inactive: bool = False,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_module_access(MODULE, AccessLevel.VIEW)),
):
    query = db.query(GLType).filter(GLType.company_id == current_user.company_id)
    if not include_inactive:
        query = query.filter(GLType.is_active)
    return query.order_by(GLType.account_type, GLType.code).all()


@router.post("", response_model=GLTypeOut)
def create_gl_type(
    payload: GLTypeCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_module_access(MODULE, AccessLevel.EDIT)),
):
    existing = (
        db.query(GLType)
        .filter(GLType.company_id == current_user.company_id, GLType.code == payload.code)
        .first()
    )
    if existing:
        raise HTTPException(status_code=409, detail=f"GL Type code {payload.code} already exists.")

    gl_type = GLType(company_id=current_user.company_id, **payload.model_dump())
    db.add(gl_type)
    db.flush()
    audit.record(
        db,
        entity_type="gl_type",
        entity_id=gl_type.id,
        action="created",
        actor_user_id=current_user.id,
        details=f"{payload.code} {payload.name}",
        new_value={"code": payload.code, "name": payload.name, "account_type": payload.account_type.value},
    )
    db.commit()
    db.refresh(gl_type)
    return gl_type


@router.patch("/{gl_type_id}", response_model=GLTypeOut)
def update_gl_type(
    gl_type_id: uuid.UUID,
    payload: GLTypeUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_module_access(MODULE, AccessLevel.EDIT)),
):
    gl_type = db.get(GLType, gl_type_id)
    if not gl_type or gl_type.company_id != current_user.company_id:
        raise HTTPException(status_code=404, detail="GL Type not found")

    fields = payload.model_dump(exclude_unset=True)
    old_value: dict[str, object] = {}
    new_value: dict[str, object] = {}
    for field in ("code", "name", "account_type", "is_active"):
        if field not in fields:
            continue
        old = getattr(gl_type, field)
        new = fields[field]
        if old == new:
            continue
        old_value[field] = old.value if hasattr(old, "value") else old
        new_value[field] = new.value if hasattr(new, "value") else new
        setattr(gl_type, field, new)

    audit.record(
        db,
        entity_type="gl_type",
        entity_id=gl_type.id,
        action="updated",
        actor_user_id=current_user.id,
        details=f"{gl_type.code} {gl_type.name}",
        old_value=old_value or None,
        new_value=new_value or None,
    )
    db.commit()
    db.refresh(gl_type)
    return gl_type
