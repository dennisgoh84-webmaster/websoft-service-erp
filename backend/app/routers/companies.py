"""
Company Setup / multi-company.

One company today (Webmaster Consultancy Pte Ltd), but CLAUDE.md's
approved architecture anticipates more, so this module owns:
- the company record itself (name, country, currency, timezone, logo),
- which companies each staff member may work in (UserCompanyAccess),
- switching the company a staff member is currently working in.

Every company-owned record already carries a `company_id` and is
filtered by `current_user.company_id`, so switching company re-scopes
the whole application (dashboard, customers, contracts, job orders,
service records, invoices, groups, staff, event logs) automatically.
"""
import uuid

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.deps import get_current_user
from app.models.core import Company, User, UserCompanyAccess, UserRole
from app.models.groups import AccessLevel, Group, GroupModuleAuthority
from app.models.licensing import CompanyModule, LicenseType, Module
from app.schemas.schemas import CompanyCreate, CompanyOut, CompanyUpdate
from app.services import audit
from app.services.authority import require_module_access

router = APIRouter(prefix="/api/companies", tags=["companies"])
MODULE = "core_administration"

# A logo is UI branding held inline as a data URI (see Company.logo);
# keep it small enough that shipping it with every page load is cheap.
MAX_LOGO_CHARS = 400_000  # ~300 KB of base64


def _validate_logo(logo: str | None) -> None:
    if logo is None:
        return
    if not logo.startswith("data:image/"):
        raise HTTPException(
            status_code=400,
            detail="Logo must be an image data URI (e.g. 'data:image/png;base64,...').",
        )
    if len(logo) > MAX_LOGO_CHARS:
        raise HTTPException(
            status_code=400, detail="Logo image is too large -- please use an image under ~300 KB."
        )


def _accessible_company_ids(db: Session, user: User) -> set[uuid.UUID]:
    """Companies this user may switch to. The owner can reach every
    company (they own the entities); everyone else is limited to their
    explicit UserCompanyAccess rows, plus their current company so they
    can never be stranded without one."""
    if user.role == UserRole.OWNER:
        return {c.id for c in db.query(Company.id).all()}
    rows = db.query(UserCompanyAccess).filter(UserCompanyAccess.user_id == user.id).all()
    return {r.company_id for r in rows} | {user.company_id}


@router.get("", response_model=list[CompanyOut])
def list_my_companies(
    db: Session = Depends(get_db),
    # Deliberately NOT gated by core_administration: every signed-in
    # user needs their own company's name/logo for the app header, and
    # the list of companies they may switch to. Creating/editing a
    # company below IS gated.
    current_user: User = Depends(get_current_user),
):
    ids = _accessible_company_ids(db, current_user)
    return (
        db.query(Company)
        .filter(Company.id.in_(ids), Company.is_active)
        .order_by(Company.name)
        .all()
    )


@router.post("", response_model=CompanyOut)
def create_company(
    payload: CompanyCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_module_access(MODULE, AccessLevel.FULL)),
):
    _validate_logo(payload.logo)
    company = Company(
        name=payload.name,
        country=payload.country,
        currency=payload.currency,
        timezone=payload.timezone,
        logo=payload.logo,
    )
    db.add(company)
    db.flush()

    # A new company starts with the same module catalog, all disabled
    # except the ones already built -- Module Control is per-company, so
    # each entity can run a different module mix from here.
    built_module_keys = []
    for module in db.query(Module).all():
        if module.is_built:
            built_module_keys.append(module.key)
        db.add(
            CompanyModule(
                company_id=company.id,
                module_key=module.key,
                enabled=module.is_built,
                license_type=LicenseType.INCLUDED,
            )
        )

    # Groups are per company, so a brand-new company starts with none --
    # which would leave nothing to assign staff to. Bootstrap one admin
    # group with full access to the built modules; it is editable in
    # Group Authority like any other.
    admin_group = Group(
        company_id=company.id,
        name="Owner / Admin",
        description="Full access to every module in this company. Created with the company.",
    )
    db.add(admin_group)
    db.flush()
    for module_key in built_module_keys:
        db.add(
            GroupModuleAuthority(
                group_id=admin_group.id, module_key=module_key, access_level=AccessLevel.FULL
            )
        )

    # Whoever created it can work in it, as an admin there.
    db.add(
        UserCompanyAccess(
            user_id=current_user.id, company_id=company.id, group_id=admin_group.id
        )
    )

    audit.record(
        db,
        entity_type="company",
        entity_id=company.id,
        action="created",
        actor_user_id=current_user.id,
        details=f"name={payload.name}",
        new_value={
            "name": payload.name,
            "country": payload.country,
            "currency": payload.currency,
            "timezone": payload.timezone,
        },
    )
    db.commit()
    db.refresh(company)
    return company


@router.patch("/{company_id}", response_model=CompanyOut)
def update_company(
    company_id: uuid.UUID,
    payload: CompanyUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_module_access(MODULE, AccessLevel.FULL)),
):
    company = db.get(Company, company_id)
    if not company:
        raise HTTPException(status_code=404, detail="Company not found")
    if company.id not in _accessible_company_ids(db, current_user):
        raise HTTPException(status_code=403, detail="You cannot manage this company.")

    fields = payload.model_dump(exclude_unset=True)
    if "logo" in fields:
        _validate_logo(fields["logo"])

    old_value: dict[str, object] = {}
    new_value: dict[str, object] = {}
    for field in (
        "name",
        "country",
        "currency",
        "timezone",
        "is_active",
        "logo",
        "address",
        "gst_registration_no",
        "write_off_approval_threshold_sgd",
        "credit_note_approval_threshold_sgd",
        "po_approval_threshold_sgd",
    ):
        if field not in fields:
            continue
        old = getattr(company, field)
        new = fields[field]
        if old == new:
            continue
        if field == "logo":
            # Never dump base64 image data into the audit trail -- record
            # that it changed, not the pixels.
            old_value[field] = "(image set)" if old else "(none)"
            new_value[field] = "(image set)" if new else "(none)"
        else:
            old_value[field] = old
            new_value[field] = new
        setattr(company, field, new)

    audit.record(
        db,
        entity_type="company",
        entity_id=company.id,
        action="updated",
        actor_user_id=current_user.id,
        old_value=old_value or None,
        new_value=new_value or None,
    )
    db.commit()
    db.refresh(company)
    return company


@router.post("/{company_id}/switch", response_model=CompanyOut)
def switch_company(
    company_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Change the company this user is working in. Everything they see
    is scoped to `User.company_id`, so this one write re-scopes the
    whole application for them."""
    company = db.get(Company, company_id)
    if not company or not company.is_active:
        raise HTTPException(status_code=404, detail="Company not found")
    if company.id not in _accessible_company_ids(db, current_user):
        raise HTTPException(
            status_code=403, detail="You do not have access to this company."
        )

    previous = db.get(Company, current_user.company_id)
    if company.id != current_user.company_id:
        audit.record(
            db,
            entity_type="user",
            entity_id=current_user.id,
            action="switched_company",
            actor_user_id=current_user.id,
            old_value={"company": previous.name if previous else None},
            new_value={"company": company.name},
        )
        current_user.company_id = company.id
    db.commit()
    db.refresh(company)
    return company
