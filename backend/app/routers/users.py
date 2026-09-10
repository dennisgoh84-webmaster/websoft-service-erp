"""
Staff Master -- the list of staff/user accounts, their role (for the
named-responsibility business rules) and their Group (for Group
Authority / general module security). See app/models/core.py for the
two-axis RBAC design rationale.
"""
import uuid

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.deps import get_current_user
from app.models.core import AuditLogEntry, User
from app.models.groups import AccessLevel, Group
from app.schemas.schemas import AuditLogEntryOut, UserCreate, UserOut, UserPasswordReset, UserUpdate
from app.services import audit
from app.services.auth import hash_password
from app.services.authority import require_module_access

router = APIRouter(prefix="/api/users", tags=["users"])
MODULE = "core_administration"


def _get_user_or_404(db: Session, user_id: uuid.UUID) -> User:
    user = db.get(User, user_id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    return user


@router.get("", response_model=list[UserOut])
def list_users(
    include_inactive: bool = False,
    db: Session = Depends(get_db),
    # Deliberately NOT gated by core_administration: this basic staff
    # directory (name/role) is used across other modules too, e.g. the
    # "assign to" picker on a Job Order -- any signed-in user may read it.
    # Staff Master's mutating actions below (create/update/deactivate/
    # reset-password) and single-record lookup ARE gated.
    current_user: User = Depends(get_current_user),
):
    query = db.query(User).filter(User.company_id == current_user.company_id)
    if not include_inactive:
        query = query.filter(User.is_active)
    return query.order_by(User.full_name).all()


@router.post("", response_model=UserOut)
def create_user(
    payload: UserCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_module_access(MODULE, AccessLevel.FULL)),
):
    if db.query(User).filter(User.email == payload.email).first():
        raise HTTPException(status_code=409, detail="A user with this email already exists.")
    if payload.group_id is not None and not db.get(Group, payload.group_id):
        raise HTTPException(status_code=400, detail="Unknown group_id")

    user = User(
        company_id=current_user.company_id,
        email=payload.email,
        hashed_password=hash_password(payload.password),
        full_name=payload.full_name,
        role=payload.role,
        group_id=payload.group_id,
    )
    db.add(user)
    db.flush()
    audit.record(
        db,
        entity_type="user",
        entity_id=user.id,
        action="created",
        actor_user_id=current_user.id,
        details=f"email={payload.email}, role={payload.role.value}",
        new_value={
            "email": payload.email,
            "full_name": payload.full_name,
            "role": payload.role.value,
            "group_id": str(payload.group_id) if payload.group_id else None,
        },
    )
    db.commit()
    db.refresh(user)
    return user


@router.get("/{user_id}", response_model=UserOut)
def get_user(
    user_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_module_access(MODULE, AccessLevel.VIEW)),
):
    return _get_user_or_404(db, user_id)


@router.get("/{user_id}/audit-log", response_model=list[AuditLogEntryOut])
def get_user_audit_log(
    user_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_module_access(MODULE, AccessLevel.VIEW)),
):
    """Recent Staff Master activity for this account (created, role/group
    changes, deactivate/reactivate, password resets) -- the audit trail
    CLAUDE.md requires for account-affecting actions."""
    _get_user_or_404(db, user_id)
    return (
        db.query(AuditLogEntry)
        .filter(AuditLogEntry.entity_type == "user", AuditLogEntry.entity_id == user_id)
        .order_by(AuditLogEntry.at.desc())
        .limit(50)
        .all()
    )


@router.patch("/{user_id}", response_model=UserOut)
def update_user(
    user_id: uuid.UUID,
    payload: UserUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_module_access(MODULE, AccessLevel.FULL)),
):
    user = _get_user_or_404(db, user_id)
    fields = payload.model_dump(exclude_unset=True)
    if "group_id" in fields and fields["group_id"] is not None and not db.get(Group, fields["group_id"]):
        raise HTTPException(status_code=400, detail="Unknown group_id")

    old_value: dict[str, str | None] = {}
    new_value: dict[str, str | None] = {}

    def _apply(field: str, new: object) -> None:
        old = getattr(user, field)
        if old != new:
            old_value[field] = old.value if hasattr(old, "value") else (str(old) if old is not None else None)
            new_value[field] = new.value if hasattr(new, "value") else (str(new) if new is not None else None)
        setattr(user, field, new)

    if "full_name" in fields:
        _apply("full_name", fields["full_name"])
    if "role" in fields:
        _apply("role", fields["role"])
    if "group_id" in fields:
        # Explicitly provided, even if null -- distinguishes "clear the
        # group" from "field omitted" (see UserUpdate: group_id defaults
        # to None either way, so `is not None` alone can't tell them apart).
        _apply("group_id", fields["group_id"])

    audit.record(
        db,
        entity_type="user",
        entity_id=user.id,
        action="updated",
        actor_user_id=current_user.id,
        old_value=old_value or None,
        new_value=new_value or None,
    )
    db.commit()
    db.refresh(user)
    return user


@router.post("/{user_id}/deactivate", response_model=UserOut)
def deactivate_user(
    user_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_module_access(MODULE, AccessLevel.FULL)),
):
    user = _get_user_or_404(db, user_id)
    if user.id == current_user.id:
        raise HTTPException(status_code=400, detail="You cannot deactivate your own account.")
    user.is_active = False
    audit.record(
        db,
        entity_type="user",
        entity_id=user.id,
        action="deactivated",
        actor_user_id=current_user.id,
        old_value={"is_active": True},
        new_value={"is_active": False},
    )
    db.commit()
    db.refresh(user)
    return user


@router.post("/{user_id}/reactivate", response_model=UserOut)
def reactivate_user(
    user_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_module_access(MODULE, AccessLevel.FULL)),
):
    user = _get_user_or_404(db, user_id)
    user.is_active = True
    audit.record(
        db,
        entity_type="user",
        entity_id=user.id,
        action="reactivated",
        actor_user_id=current_user.id,
        old_value={"is_active": False},
        new_value={"is_active": True},
    )
    db.commit()
    db.refresh(user)
    return user


@router.post("/{user_id}/reset-password", response_model=UserOut)
def reset_password(
    user_id: uuid.UUID,
    payload: UserPasswordReset,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_module_access(MODULE, AccessLevel.FULL)),
):
    user = _get_user_or_404(db, user_id)
    user.hashed_password = hash_password(payload.new_password)
    audit.record(
        db,
        entity_type="user",
        entity_id=user.id,
        action="password_reset",
        actor_user_id=current_user.id,
    )
    db.commit()
    db.refresh(user)
    return user
