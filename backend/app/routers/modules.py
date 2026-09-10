"""
Module Control -- lets an owner see and toggle which business-area
modules are enabled/licensed for their company. See
app/models/licensing.py for the data model rationale.
"""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.models.core import User
from app.models.groups import AccessLevel
from app.models.licensing import CompanyModule, Module
from app.schemas.schemas import ModuleOut, ModuleToggleRequest
from app.services import audit
from app.services.authority import require_module_access
from datetime import datetime, timezone

router = APIRouter(prefix="/api/modules", tags=["modules"])
MODULE = "core_administration"


@router.get("", response_model=list[ModuleOut])
def list_modules(
    db: Session = Depends(get_db),
    current_user: User = Depends(require_module_access(MODULE, AccessLevel.VIEW)),
):
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
    current_user: User = Depends(require_module_access(MODULE, AccessLevel.FULL)),
):
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
        db.flush()

    old_value = {"enabled": cm.enabled, "license_type": cm.license_type.value}

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
        old_value=old_value,
        new_value={"enabled": cm.enabled, "license_type": cm.license_type.value},
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
