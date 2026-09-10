"""
Group Authority enforcement -- the per-module security layer, controlled
by which Group a user belongs to (see app/models/groups.py for the
design rationale).

Usage in a router:

    from app.services.authority import require_module_access
    from app.models.groups import AccessLevel

    @router.get("", ...)
    def list_things(
        db: Session = Depends(get_db),
        current_user: User = Depends(require_module_access("service_contracts", AccessLevel.VIEW)),
    ):
        ...

The owner role always passes every check -- Dennis is never locked out
of his own system by a misconfigured group.
"""
import uuid

from fastapi import Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.deps import get_current_user
from app.models.core import User, UserCompanyAccess, UserRole
from app.models.groups import ACCESS_LEVEL_ORDER, AccessLevel, GroupModuleAuthority


def get_user_group_id(db: Session, user: User, company_id: uuid.UUID | None = None):
    """The Group this user holds in a given company (defaults to the one
    they are currently working in). The assignment lives on
    UserCompanyAccess, because a staff member has a Group *per company*
    -- see app/models/core.py."""
    access = (
        db.query(UserCompanyAccess)
        .filter(
            UserCompanyAccess.user_id == user.id,
            UserCompanyAccess.company_id == (company_id or user.company_id),
        )
        .first()
    )
    return access.group_id if access else None


def get_access_level(db: Session, user: User, module_key: str) -> AccessLevel:
    if user.role == UserRole.OWNER:
        return AccessLevel.FULL
    group_id = get_user_group_id(db, user)
    if group_id is None:
        return AccessLevel.NONE
    row = (
        db.query(GroupModuleAuthority)
        .filter(
            GroupModuleAuthority.group_id == group_id,
            GroupModuleAuthority.module_key == module_key,
        )
        .first()
    )
    return row.access_level if row else AccessLevel.NONE


def has_access(db: Session, user: User, module_key: str, min_level: AccessLevel) -> bool:
    return ACCESS_LEVEL_ORDER[get_access_level(db, user, module_key)] >= ACCESS_LEVEL_ORDER[min_level]


def require_module_access(module_key: str, min_level: AccessLevel):
    """FastAPI dependency factory: use in place of a plain
    `Depends(get_current_user)` on any route that touches `module_key`."""

    def dependency(
        db: Session = Depends(get_db), current_user: User = Depends(get_current_user)
    ) -> User:
        if not has_access(db, current_user, module_key, min_level):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=(
                    f"Your group does not have {min_level.value} access to "
                    f"the '{module_key}' module."
                ),
            )
        return current_user

    return dependency
