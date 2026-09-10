"""
Group Authority admin API -- create/manage Groups and set each Group's
per-module access level. See app/models/groups.py for the design
rationale and app/services/authority.py for how it is enforced.
"""
import uuid

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session, selectinload

from app.core.database import get_db
from app.models.core import User
from app.models.groups import AccessLevel, Group, GroupModuleAuthority
from app.models.licensing import Module
from app.schemas.schemas import (
    GroupAuthoritiesUpdateRequest,
    GroupCreate,
    GroupOut,
    GroupUpdate,
)
from app.services import audit
from app.services.authority import require_module_access

router = APIRouter(prefix="/api/groups", tags=["groups"])
MODULE = "core_administration"


def _get_group_or_404(db: Session, group_id: uuid.UUID) -> Group:
    group = (
        db.query(Group)
        .options(selectinload(Group.authorities))
        .filter(Group.id == group_id)
        .first()
    )
    if not group:
        raise HTTPException(status_code=404, detail="Group not found")
    return group


def _member_count(db: Session, group_id: uuid.UUID) -> int:
    return db.query(User).filter(User.group_id == group_id).count()


@router.post("", response_model=GroupOut)
def create_group(
    payload: GroupCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_module_access(MODULE, AccessLevel.FULL)),
):
    group = Group(
        company_id=current_user.company_id,
        name=payload.name,
        description=payload.description,
    )
    db.add(group)
    db.flush()
    audit.record(
        db,
        entity_type="group",
        entity_id=group.id,
        action="created",
        actor_user_id=current_user.id,
        details=f"name={payload.name}",
        new_value={"name": payload.name, "description": payload.description},
    )
    db.commit()
    db.refresh(group)
    return GroupOut.from_model(group, member_count=0)


@router.get("", response_model=list[GroupOut])
def list_groups(
    db: Session = Depends(get_db),
    current_user: User = Depends(require_module_access(MODULE, AccessLevel.VIEW)),
):
    groups = (
        db.query(Group)
        .options(selectinload(Group.authorities))
        .filter(Group.company_id == current_user.company_id)
        .order_by(Group.name)
        .all()
    )
    return [GroupOut.from_model(g, member_count=_member_count(db, g.id)) for g in groups]


@router.get("/{group_id}", response_model=GroupOut)
def get_group(
    group_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_module_access(MODULE, AccessLevel.VIEW)),
):
    group = _get_group_or_404(db, group_id)
    return GroupOut.from_model(group, member_count=_member_count(db, group.id))


@router.patch("/{group_id}", response_model=GroupOut)
def update_group(
    group_id: uuid.UUID,
    payload: GroupUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_module_access(MODULE, AccessLevel.FULL)),
):
    group = _get_group_or_404(db, group_id)
    fields = payload.model_dump(exclude_unset=True)
    old_value: dict[str, str | None] = {}
    new_value: dict[str, str | None] = {}
    if "name" in fields and fields["name"] != group.name:
        old_value["name"], new_value["name"] = group.name, fields["name"]
        group.name = fields["name"]
    if "description" in fields and fields["description"] != group.description:
        old_value["description"], new_value["description"] = group.description, fields["description"]
        group.description = fields["description"]  # explicitly provided; null clears it
    audit.record(
        db,
        entity_type="group",
        entity_id=group.id,
        action="updated",
        actor_user_id=current_user.id,
        old_value=old_value or None,
        new_value=new_value or None,
    )
    db.commit()
    db.refresh(group)
    return GroupOut.from_model(group, member_count=_member_count(db, group.id))


@router.delete("/{group_id}", status_code=204)
def delete_group(
    group_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_module_access(MODULE, AccessLevel.FULL)),
):
    group = _get_group_or_404(db, group_id)
    if _member_count(db, group.id) > 0:
        raise HTTPException(
            status_code=409,
            detail="Cannot delete a Group that still has staff assigned to it. "
            "Reassign those staff to another Group first.",
        )
    audit.record(
        db,
        entity_type="group",
        entity_id=group.id,
        action="deleted",
        actor_user_id=current_user.id,
        details=f"name={group.name}",
        old_value={"name": group.name, "description": group.description},
    )
    db.delete(group)
    db.commit()


@router.put("/{group_id}/authorities", response_model=GroupOut)
def set_group_authorities(
    group_id: uuid.UUID,
    payload: GroupAuthoritiesUpdateRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_module_access(MODULE, AccessLevel.FULL)),
):
    group = _get_group_or_404(db, group_id)
    valid_module_keys = {m.key for m in db.query(Module.key).all()}
    existing = {a.module_key: a for a in group.authorities}

    old_value: dict[str, str] = {}
    new_value: dict[str, str] = {}
    for entry in payload.authorities:
        if entry.module_key not in valid_module_keys:
            raise HTTPException(status_code=400, detail=f"Unknown module '{entry.module_key}'")
        row = existing.get(entry.module_key)
        prior_level = row.access_level if row else AccessLevel.NONE
        if prior_level != entry.access_level:
            old_value[entry.module_key] = prior_level.value
            new_value[entry.module_key] = entry.access_level.value
        if row:
            row.access_level = entry.access_level
        else:
            db.add(
                GroupModuleAuthority(
                    group_id=group.id,
                    module_key=entry.module_key,
                    access_level=entry.access_level,
                )
            )

    audit.record(
        db,
        entity_type="group",
        entity_id=group.id,
        action="authorities_updated",
        actor_user_id=current_user.id,
        details=", ".join(f"{e.module_key}={e.access_level.value}" for e in payload.authorities),
        old_value=old_value or None,
        new_value=new_value or None,
    )
    db.commit()
    return GroupOut.from_model(_get_group_or_404(db, group_id), member_count=_member_count(db, group_id))
