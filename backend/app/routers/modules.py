"""
Module Control -- lets an owner see and toggle which business-area
modules are enabled/licensed for their company. See
app/models/licensing.py for the data model rationale.
"""
import uuid

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.deps import get_current_user
from app.models.core import User, UserRole
from app.models.licensing import CompanyModule, Module
from app.schemas.schemas import ModuleOut, ModuleToggleRequest
from app.services import audit
from datetime import datetime, timezone

router = APIRouter(prefix="/api/modules", tags=["modules"])


def _require_owner(user: User):
    if user.role != UserRole.OWNER:
        raise HTTPException(status_code=403, detail="Only the owner can manage module licensing.")


@router.get("", response_model=list[ModuleOut])
def list_modules(db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    modules = db.query(Module).order_by(Module.key).all()
    company_modules = {
        cm.module_key: cm
        for cm in db.query(CompanyModule).filter(CompanyModule.company_id == current_user.company_id)
    }
    out = []
    for m in modules:
        cm = company_modules.get(m.key)
        out.append(
            ModuleOut(
                key=m.key,
                name=m.name,
                description=m.description,
                is_built=m.is_built,
                enabled=cm.enabled if cm else False,
                license_type=cm.license_type if cm else "included",
            )
        )
    return out


@router.post("/{module_key}/toggle", response_model=ModuleOut)
def toggle_module(
    module_key: str,
    payload: ModuleToggleRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    _require_owner(current_user)
    module = db.get(Module, module_key)
    if not module:
        raise HTTPException(status_code=404, detail="Module not found")

    cm = (
        db.query(CompanyModule)
        .filter(
            CompanyModule.company_id == current_user.company_id,
            CompanyModule.module_key == module_key,
        )
        .first()
    )
    if not cm:
        cm = CompanyModule(company_id=current_user.company_id, module_key=module_key)
        db.add(cm)

    cm.enabled = payload.enabled
    if payload.license_type is not None:
        cm.license_type = payload.license_type
    if payload.notes is not None:
        cm.notes = payload.notes
    if payload.enabled:
        cm.enabled_at = datetime.now(timezone.utc)

    audit.record(
        db,
        entity_type="company_module",
        entity_id=cm.id,
        action="toggled",
        actor_user_id=current_user.id,
        details=f"module={module_key}, enabled={payload.enabled}",
    )
    db.commit()

    return ModuleOut(
        key=module.key,
        name=module.name,
        description=module.description,
        is_built=module.is_built,
        enabled=cm.enabled,
        license_type=cm.license_type,
    )
