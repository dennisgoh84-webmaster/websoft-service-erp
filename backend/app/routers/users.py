"""
Staff Master -- the list of staff/user accounts, their role (for the
named-responsibility business rules) and their Group (for Group
Authority / general module security). See app/models/core.py for the
two-axis RBAC design rationale.

Multi-company: a staff member holds a Group **per company** they work
in, stored on UserCompanyAccess. The `group_id` on the endpoints below
always means "their Group in the company you are currently working in";
the per-company view/edit lives on /company-access.
"""
import uuid

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.deps import get_current_user
from app.models.core import AuditLogEntry, Company, User, UserCompanyAccess
from app.models.groups import AccessLevel, Group
from app.schemas.schemas import (
    AuditLogEntryOut,
    UserCompanyAccessOut,
    UserCompanyAccessUpdate,
    UserCreate,
    UserOut,
    UserPasswordReset,
    UserUpdate,
)
from app.services import audit, exports
from app.services.auth import hash_password, validate_password_complexity
from app.services.authority import require_module_access

router = APIRouter(prefix="/api/users", tags=["users"])
MODULE = "core_administration"

USER_EXPORT_FIELDS = ["full_name", "email", "role", "group_name", "is_active"]

# A staff photo is held inline as a data URI (User.photo), same pattern
# and size cap rationale as Company.logo in app/routers/companies.py.
MAX_PHOTO_CHARS = 400_000  # ~300 KB of base64


def _validate_photo(photo: str | None) -> None:
    if photo is None:
        return
    if not photo.startswith("data:image/"):
        raise HTTPException(
            status_code=400,
            detail="Photo must be an image data URI (e.g. 'data:image/png;base64,...').",
        )
    if len(photo) > MAX_PHOTO_CHARS:
        raise HTTPException(
            status_code=400, detail="Photo is too large -- please use an image under ~300 KB."
        )


def _get_user_or_404(db: Session, user_id: uuid.UUID) -> User:
    user = db.get(User, user_id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    return user


def _access_row(db: Session, user_id: uuid.UUID, company_id: uuid.UUID):
    return (
        db.query(UserCompanyAccess)
        .filter(
            UserCompanyAccess.user_id == user_id,
            UserCompanyAccess.company_id == company_id,
        )
        .first()
    )


def _validate_group_for_company(db: Session, group_id: uuid.UUID | None, company_id: uuid.UUID):
    """A Group only means something inside its own company, so refuse to
    assign one belonging to a different entity."""
    if group_id is None:
        return
    group = db.get(Group, group_id)
    if not group:
        raise HTTPException(status_code=400, detail="Unknown group_id")
    if group.company_id != company_id:
        raise HTTPException(
            status_code=400, detail="That Group belongs to a different company."
        )


def _user_out(db: Session, user: User, company_id: uuid.UUID) -> UserOut:
    """UserOut with `group_id` resolved to this user's Group in the given
    company (Group is per company -- see the module docstring)."""
    access = _access_row(db, user.id, company_id)
    return UserOut(
        id=user.id,
        full_name=user.full_name,
        email=user.email,
        role=user.role,
        group_id=access.group_id if access else None,
        photo=user.photo,
        must_change_password=user.must_change_password,
        is_active=user.is_active,
        created_at=user.created_at,
    )


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
    return [_user_out(db, u, current_user.company_id) for u in query.order_by(User.full_name).all()]


def _users_for_export(db: Session, company_id: uuid.UUID, include_inactive: bool) -> list[dict]:
    query = db.query(User).filter(User.company_id == company_id)
    if not include_inactive:
        query = query.filter(User.is_active)
    users = query.order_by(User.full_name).all()
    group_ids = {
        a.group_id
        for a in db.query(UserCompanyAccess).filter(
            UserCompanyAccess.user_id.in_({u.id for u in users}), UserCompanyAccess.company_id == company_id
        )
        if a.group_id
    } if users else set()
    group_names = {g.id: g.name for g in db.query(Group).filter(Group.id.in_(group_ids))} if group_ids else {}
    rows = []
    for u in users:
        out = _user_out(db, u, company_id)
        rows.append(
            {
                "full_name": u.full_name,
                "email": u.email,
                "role": out.role.value,
                "group_name": group_names.get(out.group_id, "") if out.group_id else "",
                "is_active": u.is_active,
            }
        )
    return rows


@router.get("/export.csv")
def export_users_csv(
    include_inactive: bool = False,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    rows = _users_for_export(db, current_user.company_id, include_inactive)
    csv_text = exports.rows_to_csv(USER_EXPORT_FIELDS, rows)
    return StreamingResponse(
        iter([csv_text]),
        media_type="text/csv",
        headers={"Content-Disposition": "attachment; filename=staff-master.csv"},
    )


@router.get("/export.xlsx")
def export_users_excel(
    include_inactive: bool = False,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    rows = _users_for_export(db, current_user.company_id, include_inactive)
    data = exports.rows_to_excel(USER_EXPORT_FIELDS, rows, sheet_name="Staff Master")
    return StreamingResponse(
        iter([data]),
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": "attachment; filename=staff-master.xlsx"},
    )


@router.post("", response_model=UserOut)
def create_user(
    payload: UserCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_module_access(MODULE, AccessLevel.FULL)),
):
    if db.query(User).filter(User.email == payload.email).first():
        raise HTTPException(status_code=409, detail="A user with this email already exists.")
    _validate_group_for_company(db, payload.group_id, current_user.company_id)
    try:
        validate_password_complexity(payload.password)
    except ValueError as e:
        raise HTTPException(status_code=422, detail=str(e)) from e

    user = User(
        company_id=current_user.company_id,
        email=payload.email,
        hashed_password=hash_password(payload.password),
        full_name=payload.full_name,
        role=payload.role,
        # Confirmed 2026-09-12: every new staff account must set its own
        # password the first time it signs in (see app/routers/auth.py).
        must_change_password=True,
    )
    db.add(user)
    db.flush()

    # New staff start with access to the company they were created in,
    # with the Group chosen for them there.
    db.add(
        UserCompanyAccess(
            user_id=user.id, company_id=current_user.company_id, group_id=payload.group_id
        )
    )

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
    return _user_out(db, user, current_user.company_id)


@router.get("/{user_id}", response_model=UserOut)
def get_user(
    user_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_module_access(MODULE, AccessLevel.VIEW)),
):
    return _user_out(db, _get_user_or_404(db, user_id), current_user.company_id)


@router.get("/{user_id}/company-access", response_model=list[UserCompanyAccessOut])
def get_user_company_access(
    user_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_module_access(MODULE, AccessLevel.VIEW)),
):
    """Which companies this staff member may work in, and their Group in
    each (Group is per company)."""
    _get_user_or_404(db, user_id)
    rows = db.query(UserCompanyAccess).filter(UserCompanyAccess.user_id == user_id).all()
    out = []
    for row in rows:
        company = db.get(Company, row.company_id)
        group = db.get(Group, row.group_id) if row.group_id else None
        out.append(
            UserCompanyAccessOut(
                company_id=row.company_id,
                company_name=company.name if company else "(unknown)",
                group_id=row.group_id,
                group_name=group.name if group else None,
            )
        )
    return out


@router.put("/{user_id}/company-access", response_model=list[UserCompanyAccessOut])
def set_user_company_access(
    user_id: uuid.UUID,
    payload: UserCompanyAccessUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_module_access(MODULE, AccessLevel.FULL)),
):
    """Replace the set of companies this staff member may work in, and
    their Group in each. Omitting a company revokes access to it."""
    user = _get_user_or_404(db, user_id)

    requested = {e.company_id: e.group_id for e in payload.access}
    for company_id, group_id in requested.items():
        if not db.get(Company, company_id):
            raise HTTPException(status_code=400, detail="Unknown company_id")
        _validate_group_for_company(db, group_id, company_id)

    existing = {
        r.company_id: r
        for r in db.query(UserCompanyAccess).filter(UserCompanyAccess.user_id == user_id).all()
    }

    old_value: dict[str, str | None] = {}
    new_value: dict[str, str | None] = {}

    def _label(company_id: uuid.UUID, group_id: uuid.UUID | None) -> str:
        group = db.get(Group, group_id) if group_id else None
        return group.name if group else "(no group)"

    # Revoke companies no longer listed -- but never strand someone in a
    # company they are currently working in.
    for company_id, row in existing.items():
        if company_id in requested:
            continue
        if company_id == user.company_id:
            raise HTTPException(
                status_code=400,
                detail="Cannot revoke access to the company this staff member is currently working in.",
            )
        company = db.get(Company, company_id)
        old_value[company.name if company else str(company_id)] = _label(company_id, row.group_id)
        new_value[company.name if company else str(company_id)] = "(no access)"
        db.delete(row)

    # Add or re-group the rest.
    for company_id, group_id in requested.items():
        company = db.get(Company, company_id)
        key = company.name if company else str(company_id)
        row = existing.get(company_id)
        if row is None:
            old_value[key] = "(no access)"
            new_value[key] = _label(company_id, group_id)
            db.add(UserCompanyAccess(user_id=user_id, company_id=company_id, group_id=group_id))
        elif row.group_id != group_id:
            old_value[key] = _label(company_id, row.group_id)
            new_value[key] = _label(company_id, group_id)
            row.group_id = group_id

    audit.record(
        db,
        entity_type="user",
        entity_id=user.id,
        action="company_access_updated",
        actor_user_id=current_user.id,
        old_value=old_value or None,
        new_value=new_value or None,
    )
    db.commit()
    return get_user_company_access(user_id, db=db, current_user=current_user)


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
    if "photo" in fields:
        _validate_photo(fields["photo"])
        old_photo, new_photo = user.photo, fields["photo"]
        if old_photo != new_photo:
            # Never dump base64 image data into the audit trail -- record
            # that it changed, not the pixels (same as Company.logo).
            old_value["photo"] = "(image set)" if old_photo else "(none)"
            new_value["photo"] = "(image set)" if new_photo else "(none)"
        user.photo = new_photo
    if "group_id" in fields:
        # "Their Group in the company I am currently working in" -- Group
        # is per company, so this writes to the access row, not the user.
        # Explicitly provided, even if null, so clearing the Group works
        # (see UserUpdate: group_id defaults to None either way).
        new_group_id = fields["group_id"]
        _validate_group_for_company(db, new_group_id, current_user.company_id)
        access = _access_row(db, user.id, current_user.company_id)
        if access is None:
            access = UserCompanyAccess(
                user_id=user.id, company_id=current_user.company_id, group_id=new_group_id
            )
            db.add(access)
            old_value["group_id"] = None
            new_value["group_id"] = str(new_group_id) if new_group_id else None
        elif access.group_id != new_group_id:
            old_value["group_id"] = str(access.group_id) if access.group_id else None
            new_value["group_id"] = str(new_group_id) if new_group_id else None
            access.group_id = new_group_id

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
    return _user_out(db, user, current_user.company_id)


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
    return _user_out(db, user, current_user.company_id)


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
    return _user_out(db, user, current_user.company_id)


@router.post("/{user_id}/reset-password", response_model=UserOut)
def reset_password(
    user_id: uuid.UUID,
    payload: UserPasswordReset,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_module_access(MODULE, AccessLevel.FULL)),
):
    user = _get_user_or_404(db, user_id)
    try:
        validate_password_complexity(payload.new_password)
    except ValueError as e:
        raise HTTPException(status_code=422, detail=str(e)) from e
    user.hashed_password = hash_password(payload.new_password)
    # An admin-issued reset is a temporary password -- force the user to
    # set their own on next sign-in, same as a brand-new account.
    user.must_change_password = True
    audit.record(
        db,
        entity_type="user",
        entity_id=user.id,
        action="password_reset",
        actor_user_id=current_user.id,
    )
    db.commit()
    db.refresh(user)
    return _user_out(db, user, current_user.company_id)
