"""
Module Control -- lets an owner see and toggle which business-area
modules are enabled/licensed for their company. See
app/models/licensing.py for the data model rationale.
"""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.deps import get_current_user
from app.models.core import User, UserRole
from app.models.groups import AccessLevel
from app.models.licensing import CompanyModule, Module
from app.schemas.schemas import ModuleOut, ModuleToggleRequest
from app.services import audit
from app.services.authority import has_access, require_module_access
from datetime import datetime, timezone

router = APIRouter(prefix="/api/modules", tags=["modules"])
MODULE = "core_administration"


@router.get("/my-access", response_model=dict[str, bool])
def my_module_access(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Which built modules the current user can actually reach right now
    in their active company -- Group Authority AND Module Control both
    have to say yes (see app/services/authority.py). Used by the
    frontend nav to hide links the user has no access to, rather than
    showing a link that immediately 403s. Not itself gated by a module
    check: the app shell needs this before it knows what the user can
    see at all."""
    modules = db.query(Module).filter(Module.is_built.is_(True)).all()
    company_modules = {
        cm.module_key: cm
        for cm in db.query(CompanyModule).filter(CompanyModule.company_id == current_user.company_id)
    }
    result: dict[str, bool] = {}
    for m in modules:
        if current_user.role == UserRole.OWNER:
            # Owner bypasses both checks (see require_module_access) --
            # nav visibility mirrors that so a link he can actually use
            # isn't hidden from him.
            result[m.key] = True
            continue
        cm = company_modules.get(m.key)
        result[m.key] = bool(cm and cm.enabled) and has_access(db, current_user, m.key, AccessLevel.VIEW)
    return result


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
