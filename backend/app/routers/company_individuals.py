import uuid
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse
from sqlalchemy import or_
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.models.core import AuditLogEntry, User
from app.models.company_individuals import Branch, Contact, CompanyIndividual, CompanyIndividualGroup, CompanyIndividualRelationship
from app.models.groups import AccessLevel
from app.models.setup import SetupListItem, SetupListType
from app.schemas.schemas import (
    AuditLogEntryOut,
    BranchCreate,
    BranchOut,
    BranchUpdate,
    ContactCreate,
    ContactOut,
    ContactUpdate,
    CompanyIndividualCreate,
    CompanyIndividualOut,
    CompanyIndividualRelationshipCreate,
    CompanyIndividualRelationshipOut,
    CompanyIndividualUpdate,
    PdpaConsentUpdate,
)
from app.services import audit, exports
from app.services.authority import require_module_access

router = APIRouter(prefix="/api/company-individuals", tags=["company-individuals"])
MODULE = "company_individual_management"

CUSTOMER_EXPORT_FIELDS = [
    "name", "customer_type", "customer_group", "industry", "legacy_customer_code",
    "contact_person", "uen", "gst_registration_no", "billing_email", "phone", "mobile",
    "address", "payment_terms_days", "status",
]

CUSTOMER_FIELDS = (
    "customer_type",
    "name",
    "customer_group_id",
    "legacy_customer_code",
    "contact_person",
    "uen",
    "gst_registration_no",
    "billing_email",
    "phone",
    "mobile",
    "website",
    "address_line1",
    "address_line2",
    "address_city",
    "address_state",
    "address_postal_code",
    "address_country",
    "tags",
    "industry_code",
    "exclude_auto_sent",
    "terms_and_conditions",
    "memo",
    "billing_notes",
    "payment_terms_days",
    "data_expiry_date",
)


def _customer_or_404(db: Session, customer_id: uuid.UUID, company_id: uuid.UUID) -> CompanyIndividual:
    customer = db.get(CompanyIndividual, customer_id)
    # Multi-company: another company's customer is "not found" here.
    if not customer or customer.company_id != company_id:
        raise HTTPException(status_code=404, detail="Company / Individual not found")
    return customer


def _contact_or_404(db: Session, customer: CompanyIndividual, contact_id: uuid.UUID) -> Contact:
    contact = db.get(Contact, contact_id)
    if not contact or contact.customer_id != customer.id:
        raise HTTPException(status_code=404, detail="Contact not found")
    return contact


def _branch_or_404(db: Session, customer: CompanyIndividual, branch_id: uuid.UUID) -> Branch:
    branch = db.get(Branch, branch_id)
    if not branch or branch.customer_id != customer.id:
        raise HTTPException(status_code=404, detail="Branch not found")
    return branch


def _company_contact_or_404(db: Session, contact_id: uuid.UUID, company_id: uuid.UUID) -> Contact:
    """Unlike _contact_or_404 above, a relationship's target Contact can
    belong to ANY CompanyIndividual in this company -- not necessarily the one
    the relationship is being added from."""
    contact = db.get(Contact, contact_id)
    if not contact or contact.customer.company_id != company_id:
        raise HTTPException(status_code=404, detail="Contact not found")
    return contact


def _relationship_out(rel: CompanyIndividualRelationship) -> CompanyIndividualRelationshipOut:
    return CompanyIndividualRelationshipOut(
        id=rel.id,
        from_customer_id=rel.from_customer_id,
        to_customer_id=rel.to_customer_id,
        to_customer_name=rel.to_customer.name if rel.to_customer else None,
        to_customer_type=rel.to_customer.customer_type if rel.to_customer else None,
        to_contact_id=rel.to_contact_id,
        to_contact_name=rel.to_contact.name if rel.to_contact else None,
        to_contact_customer_id=rel.to_contact.customer_id if rel.to_contact else None,
        to_contact_customer_name=rel.to_contact.customer.name if rel.to_contact else None,
        relationship_type=rel.relationship_type,
        note=rel.note,
        is_active=rel.is_active,
        created_at=rel.created_at,
    )


@router.post("", response_model=CompanyIndividualOut)
def create_customer(
    payload: CompanyIndividualCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_module_access(MODULE, AccessLevel.EDIT)),
):
    fields = payload.model_dump()
    customer = CompanyIndividual(company_id=current_user.company_id, **fields)
    db.add(customer)
    db.flush()
    audit.record(
        db,
        entity_type="customer",
        entity_id=customer.id,
        action="created",
        actor_user_id=current_user.id,
        details=f"name={payload.name}",
        new_value={"name": payload.name, "customer_type": payload.customer_type.value},
    )
    db.commit()
    db.refresh(customer)
    return customer


@router.patch("/{customer_id}", response_model=CompanyIndividualOut)
def update_customer(
    customer_id: uuid.UUID,
    payload: CompanyIndividualUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_module_access(MODULE, AccessLevel.EDIT)),
):
    customer = _customer_or_404(db, customer_id, current_user.company_id)

    fields = payload.model_dump(exclude_unset=True)
    old_value: dict[str, object] = {}
    new_value: dict[str, object] = {}
    for field in CUSTOMER_FIELDS:
        if field not in fields:
            continue
        old = getattr(customer, field)
        new = fields[field]
        if old == new:
            continue
        old_value[field] = old.value if hasattr(old, "value") else old
        new_value[field] = new.value if hasattr(new, "value") else new
        setattr(customer, field, new)

    audit.record(
        db,
        entity_type="customer",
        entity_id=customer.id,
        action="updated",
        actor_user_id=current_user.id,
        old_value=old_value or None,
        new_value=new_value or None,
    )
    db.commit()
    db.refresh(customer)
    return customer


@router.post("/{customer_id}/deactivate", response_model=CompanyIndividualOut)
def deactivate_customer(
    customer_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_module_access(MODULE, AccessLevel.FULL)),
):
    customer = _customer_or_404(db, customer_id, current_user.company_id)
    customer.is_active = False
    audit.record(
        db,
        entity_type="customer",
        entity_id=customer.id,
        action="deactivated",
        actor_user_id=current_user.id,
        old_value={"is_active": True},
        new_value={"is_active": False},
    )
    db.commit()
    db.refresh(customer)
    return customer


@router.post("/{customer_id}/reactivate", response_model=CompanyIndividualOut)
def reactivate_customer(
    customer_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_module_access(MODULE, AccessLevel.FULL)),
):
    customer = _customer_or_404(db, customer_id, current_user.company_id)
    customer.is_active = True
    audit.record(
        db,
        entity_type="customer",
        entity_id=customer.id,
        action="reactivated",
        actor_user_id=current_user.id,
        old_value={"is_active": False},
        new_value={"is_active": True},
    )
    db.commit()
    db.refresh(customer)
    return customer


@router.post("/{customer_id}/pdpa-consent", response_model=CompanyIndividualOut)
def set_pdpa_consent(
    customer_id: uuid.UUID,
    payload: PdpaConsentUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_module_access(MODULE, AccessLevel.EDIT)),
):
    """Ticks/unticks the "PDPA Agreement e-signed" checkbox (2026-09-12).
    A dedicated endpoint rather than a field on the generic PATCH so the
    date/time is always stamped by the server, never client-supplied --
    see PdpaConsentUpdate's docstring."""
    customer = _customer_or_404(db, customer_id, current_user.company_id)
    old_given = customer.pdpa_consent_given
    customer.pdpa_consent_given = payload.given
    customer.pdpa_consent_at = datetime.now(timezone.utc) if payload.given else None
    audit.record(
        db,
        entity_type="customer",
        entity_id=customer.id,
        action="pdpa_consent_recorded" if payload.given else "pdpa_consent_revoked",
        actor_user_id=current_user.id,
        old_value={"pdpa_consent_given": old_given},
        new_value={
            "pdpa_consent_given": payload.given,
            "pdpa_consent_at": customer.pdpa_consent_at.isoformat() if customer.pdpa_consent_at else None,
        },
    )
    db.commit()
    db.refresh(customer)
    return customer


@router.post("/{customer_id}/archive", response_model=CompanyIndividualOut)
def archive_customer(
    customer_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_module_access(MODULE, AccessLevel.FULL)),
):
    """Soft-archive-in-place (confirmed 2026-09-12): all of this record's
    data stays in the same database, same row -- never deleted, moved
    to a separate schema, or exported out, per CLAUDE.md's "never
    permanently delete" rule. Typically used once `data_expiry_date`
    has passed (see CompanyIndividualDetailPage), but not restricted to
    that -- there is no background job in this system, so archiving is
    always a deliberate staff action."""
    customer = _customer_or_404(db, customer_id, current_user.company_id)
    customer.is_archived = True
    customer.archived_at = datetime.now(timezone.utc)
    audit.record(
        db,
        entity_type="customer",
        entity_id=customer.id,
        action="archived",
        actor_user_id=current_user.id,
        old_value={"is_archived": False},
        new_value={"is_archived": True},
    )
    db.commit()
    db.refresh(customer)
    return customer


@router.post("/{customer_id}/unarchive", response_model=CompanyIndividualOut)
def unarchive_customer(
    customer_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_module_access(MODULE, AccessLevel.FULL)),
):
    customer = _customer_or_404(db, customer_id, current_user.company_id)
    customer.is_archived = False
    customer.archived_at = None
    audit.record(
        db,
        entity_type="customer",
        entity_id=customer.id,
        action="unarchived",
        actor_user_id=current_user.id,
        old_value={"is_archived": True},
        new_value={"is_archived": False},
    )
    db.commit()
    db.refresh(customer)
    return customer


def _filter_customers(
    db: Session,
    company_id: uuid.UUID,
    q: str | None,
    customer_group_id: uuid.UUID | None,
    include_inactive: bool,
    industry_code: str | None = None,
    is_supplier: bool | None = None,
    include_archived: bool = False,
):
    """Dynamic filter for the CompanyIndividual master: free-text `q` matches
    across name/email/phone/mobile/UEN/legacy code/tags,
    `customer_group_id` narrows to one group of companies at a time --
    so you can search for a particular customer or pull up a whole
    group together -- and `industry_code` narrows to one industry
    (confirmed 2026-09-11: customer grouping by industry). `is_supplier`
    narrows to records flagged as a supplier (2026-09-12: Purchase
    Order/AP pick from this same file rather than a separate list).
    `include_archived` is separate from `include_inactive` -- an
    archived (past its PDPA data expiry date) record stays hidden from
    every normal list even with include_inactive=True; only the
    dedicated "show archived" view opts back in.
    Shared by list_customers and the export endpoints so "export what
    I'm looking at" always matches what's on screen."""
    query = db.query(CompanyIndividual).filter(CompanyIndividual.company_id == company_id)
    if not include_inactive:
        query = query.filter(CompanyIndividual.is_active)
    if not include_archived:
        query = query.filter(~CompanyIndividual.is_archived)
    if customer_group_id:
        query = query.filter(CompanyIndividual.customer_group_id == customer_group_id)
    if industry_code:
        query = query.filter(CompanyIndividual.industry_code == industry_code)
    if is_supplier is not None:
        query = query.filter(CompanyIndividual.is_supplier == is_supplier)
    if q:
        like = f"%{q}%"
        query = query.filter(
            or_(
                CompanyIndividual.name.ilike(like),
                CompanyIndividual.billing_email.ilike(like),
                CompanyIndividual.phone.ilike(like),
                CompanyIndividual.mobile.ilike(like),
                CompanyIndividual.contact_person.ilike(like),
                CompanyIndividual.uen.ilike(like),
                CompanyIndividual.legacy_customer_code.ilike(like),
                CompanyIndividual.tags.ilike(like),
            )
        )
    return query.order_by(CompanyIndividual.name).all()


@router.get("", response_model=list[CompanyIndividualOut])
def list_customers(
    q: str | None = None,
    customer_group_id: uuid.UUID | None = None,
    industry_code: str | None = None,
    include_inactive: bool = False,
    is_supplier: bool | None = None,
    include_archived: bool = False,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_module_access(MODULE, AccessLevel.VIEW)),
):
    return _filter_customers(
        db,
        current_user.company_id,
        q,
        customer_group_id,
        include_inactive,
        industry_code,
        is_supplier,
        include_archived,
    )


def _customer_row(customer: CompanyIndividual, group_name: str, industry_name: str) -> dict:
    address = ", ".join(
        filter(
            None,
            [
                customer.address_line1, customer.address_line2, customer.address_city,
                customer.address_state, customer.address_postal_code, customer.address_country,
            ],
        )
    )
    return {
        "name": customer.name,
        "customer_type": customer.customer_type.value,
        "customer_group": group_name,
        "industry": industry_name,
        "legacy_customer_code": customer.legacy_customer_code or "",
        "contact_person": customer.contact_person or "",
        "uen": customer.uen or "",
        "gst_registration_no": customer.gst_registration_no or "",
        "billing_email": customer.billing_email or "",
        "phone": customer.phone or "",
        "mobile": customer.mobile or "",
        "address": address,
        "payment_terms_days": customer.payment_terms_days if customer.payment_terms_days is not None else "",
        "status": "active" if customer.is_active else "inactive",
    }


def _customers_for_export(
    db: Session,
    company_id: uuid.UUID,
    q: str | None,
    customer_group_id: uuid.UUID | None,
    include_inactive: bool,
    industry_code: str | None = None,
) -> list[dict]:
    customers = _filter_customers(
        db, company_id, q, customer_group_id, include_inactive, industry_code
    )
    group_names = {g.id: g.name for g in db.query(CompanyIndividualGroup).filter(CompanyIndividualGroup.company_id == company_id)}
    industry_names = {
        i.code: i.name
        for i in db.query(SetupListItem).filter(SetupListItem.list_type == SetupListType.INDUSTRY)
    }
    return [
        _customer_row(c, group_names.get(c.customer_group_id, ""), industry_names.get(c.industry_code, ""))
        for c in customers
    ]


@router.get("/export.csv")
def export_customers_csv(
    q: str | None = None,
    customer_group_id: uuid.UUID | None = None,
    industry_code: str | None = None,
    include_inactive: bool = False,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_module_access(MODULE, AccessLevel.VIEW)),
):
    rows = _customers_for_export(
        db, current_user.company_id, q, customer_group_id, include_inactive, industry_code
    )
    csv_text = exports.rows_to_csv(CUSTOMER_EXPORT_FIELDS, rows)
    return StreamingResponse(
        iter([csv_text]),
        media_type="text/csv",
        headers={"Content-Disposition": "attachment; filename=customers.csv"},
    )


@router.get("/export.xlsx")
def export_customers_excel(
    q: str | None = None,
    customer_group_id: uuid.UUID | None = None,
    industry_code: str | None = None,
    include_inactive: bool = False,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_module_access(MODULE, AccessLevel.VIEW)),
):
    rows = _customers_for_export(
        db, current_user.company_id, q, customer_group_id, include_inactive, industry_code
    )
    data = exports.rows_to_excel(CUSTOMER_EXPORT_FIELDS, rows, sheet_name="Company Individuals")
    return StreamingResponse(
        iter([data]),
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": "attachment; filename=customers.xlsx"},
    )


@router.get("/{customer_id}", response_model=CompanyIndividualOut)
def get_customer(
    customer_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_module_access(MODULE, AccessLevel.VIEW)),
):
    return _customer_or_404(db, customer_id, current_user.company_id)


@router.get("/{customer_id}/audit-log", response_model=list[AuditLogEntryOut])
def get_customer_audit_log(
    customer_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_module_access(MODULE, AccessLevel.VIEW)),
):
    """Recent CompanyIndividual Management activity for this account (created,
    field changes, deactivate/reactivate) -- the audit trail CLAUDE.md
    requires for business-record-affecting actions."""
    _customer_or_404(db, customer_id, current_user.company_id)
    return (
        db.query(AuditLogEntry)
        .filter(AuditLogEntry.entity_type == "customer", AuditLogEntry.entity_id == customer_id)
        .order_by(AuditLogEntry.at.desc())
        .limit(50)
        .all()
    )


# ---- Contacts (contact people at a customer) -------------------------
# Modeled but previously unbuilt: no API or UI existed for these at all
# until this touch-up. Scoped under the parent customer, gated by the
# same company_individual_management module authority.


@router.get("/{customer_id}/contacts", response_model=list[ContactOut])
def list_contacts(
    customer_id: uuid.UUID,
    include_inactive: bool = False,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_module_access(MODULE, AccessLevel.VIEW)),
):
    customer = _customer_or_404(db, customer_id, current_user.company_id)
    query = db.query(Contact).filter(Contact.customer_id == customer.id)
    if not include_inactive:
        query = query.filter(Contact.is_active)
    return query.order_by(Contact.name).all()


@router.post("/{customer_id}/contacts", response_model=ContactOut)
def create_contact(
    customer_id: uuid.UUID,
    payload: ContactCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_module_access(MODULE, AccessLevel.EDIT)),
):
    customer = _customer_or_404(db, customer_id, current_user.company_id)
    contact = Contact(
        customer_id=customer.id,
        name=payload.name,
        email=payload.email,
        phone=payload.phone,
        direct_line=payload.direct_line,
    )
    db.add(contact)
    db.flush()
    audit.record(
        db,
        entity_type="contact",
        entity_id=contact.id,
        action="created",
        actor_user_id=current_user.id,
        details=f"customer={customer.name}, name={payload.name}",
        new_value={
            "name": payload.name,
            "email": payload.email,
            "phone": payload.phone,
            "direct_line": payload.direct_line,
        },
    )
    db.commit()
    db.refresh(contact)
    return contact


@router.patch("/{customer_id}/contacts/{contact_id}", response_model=ContactOut)
def update_contact(
    customer_id: uuid.UUID,
    contact_id: uuid.UUID,
    payload: ContactUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_module_access(MODULE, AccessLevel.EDIT)),
):
    customer = _customer_or_404(db, customer_id, current_user.company_id)
    contact = _contact_or_404(db, customer, contact_id)

    fields = payload.model_dump(exclude_unset=True)
    old_value: dict[str, object] = {}
    new_value: dict[str, object] = {}
    for field in ("name", "email", "phone", "direct_line"):
        if field not in fields or getattr(contact, field) == fields[field]:
            continue
        old_value[field] = getattr(contact, field)
        new_value[field] = fields[field]
        setattr(contact, field, fields[field])

    audit.record(
        db,
        entity_type="contact",
        entity_id=contact.id,
        action="updated",
        actor_user_id=current_user.id,
        old_value=old_value or None,
        new_value=new_value or None,
    )
    db.commit()
    db.refresh(contact)
    return contact


@router.post("/{customer_id}/contacts/{contact_id}/deactivate", response_model=ContactOut)
def deactivate_contact(
    customer_id: uuid.UUID,
    contact_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_module_access(MODULE, AccessLevel.EDIT)),
):
    customer = _customer_or_404(db, customer_id, current_user.company_id)
    contact = _contact_or_404(db, customer, contact_id)
    contact.is_active = False
    audit.record(
        db,
        entity_type="contact",
        entity_id=contact.id,
        action="deactivated",
        actor_user_id=current_user.id,
        old_value={"is_active": True},
        new_value={"is_active": False},
    )
    db.commit()
    db.refresh(contact)
    return contact


@router.post("/{customer_id}/contacts/{contact_id}/reactivate", response_model=ContactOut)
def reactivate_contact(
    customer_id: uuid.UUID,
    contact_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_module_access(MODULE, AccessLevel.EDIT)),
):
    customer = _customer_or_404(db, customer_id, current_user.company_id)
    contact = _contact_or_404(db, customer, contact_id)
    contact.is_active = True
    audit.record(
        db,
        entity_type="contact",
        entity_id=contact.id,
        action="reactivated",
        actor_user_id=current_user.id,
        old_value={"is_active": False},
        new_value={"is_active": True},
    )
    db.commit()
    db.refresh(contact)
    return contact


# ---- Branches (branch locations of a customer) ------------------------
# A branch is the same customer/legal entity at a different address --
# not a separate billing account. See models/customers.py docstring.


@router.get("/{customer_id}/branches", response_model=list[BranchOut])
def list_branches(
    customer_id: uuid.UUID,
    include_inactive: bool = False,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_module_access(MODULE, AccessLevel.VIEW)),
):
    customer = _customer_or_404(db, customer_id, current_user.company_id)
    query = db.query(Branch).filter(Branch.customer_id == customer.id)
    if not include_inactive:
        query = query.filter(Branch.is_active)
    return query.order_by(Branch.branch_name).all()


@router.post("/{customer_id}/branches", response_model=BranchOut)
def create_branch(
    customer_id: uuid.UUID,
    payload: BranchCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_module_access(MODULE, AccessLevel.EDIT)),
):
    customer = _customer_or_404(db, customer_id, current_user.company_id)
    branch = Branch(customer_id=customer.id, **payload.model_dump())
    db.add(branch)
    db.flush()
    audit.record(
        db,
        entity_type="branch",
        entity_id=branch.id,
        action="created",
        actor_user_id=current_user.id,
        details=f"customer={customer.name}, branch={payload.branch_name}",
        new_value={"branch_name": payload.branch_name, "branch_code": payload.branch_code},
    )
    db.commit()
    db.refresh(branch)
    return branch


@router.patch("/{customer_id}/branches/{branch_id}", response_model=BranchOut)
def update_branch(
    customer_id: uuid.UUID,
    branch_id: uuid.UUID,
    payload: BranchUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_module_access(MODULE, AccessLevel.EDIT)),
):
    customer = _customer_or_404(db, customer_id, current_user.company_id)
    branch = _branch_or_404(db, customer, branch_id)

    fields = payload.model_dump(exclude_unset=True)
    old_value: dict[str, object] = {}
    new_value: dict[str, object] = {}
    for field in (
        "branch_name", "branch_code", "address_line1", "address_line2", "address_city",
        "address_state", "address_postal_code", "address_country", "phone",
    ):
        if field not in fields or getattr(branch, field) == fields[field]:
            continue
        old_value[field] = getattr(branch, field)
        new_value[field] = fields[field]
        setattr(branch, field, fields[field])

    audit.record(
        db,
        entity_type="branch",
        entity_id=branch.id,
        action="updated",
        actor_user_id=current_user.id,
        old_value=old_value or None,
        new_value=new_value or None,
    )
    db.commit()
    db.refresh(branch)
    return branch


@router.post("/{customer_id}/branches/{branch_id}/deactivate", response_model=BranchOut)
def deactivate_branch(
    customer_id: uuid.UUID,
    branch_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_module_access(MODULE, AccessLevel.EDIT)),
):
    customer = _customer_or_404(db, customer_id, current_user.company_id)
    branch = _branch_or_404(db, customer, branch_id)
    branch.is_active = False
    audit.record(
        db,
        entity_type="branch",
        entity_id=branch.id,
        action="deactivated",
        actor_user_id=current_user.id,
        old_value={"is_active": True},
        new_value={"is_active": False},
    )
    db.commit()
    db.refresh(branch)
    return branch


@router.post("/{customer_id}/branches/{branch_id}/reactivate", response_model=BranchOut)
def reactivate_branch(
    customer_id: uuid.UUID,
    branch_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_module_access(MODULE, AccessLevel.EDIT)),
):
    customer = _customer_or_404(db, customer_id, current_user.company_id)
    branch = _branch_or_404(db, customer, branch_id)
    branch.is_active = True
    audit.record(
        db,
        entity_type="branch",
        entity_id=branch.id,
        action="reactivated",
        actor_user_id=current_user.id,
        old_value={"is_active": False},
        new_value={"is_active": True},
    )
    db.commit()
    db.refresh(branch)
    return branch


# ---- Relationships (company/individual/contact links, confirmed 2026-09-11) ----
# See CompanyIndividualRelationship's own docstring in app/models/company_individuals.py
# for why there's no separate "level" field and why this is undirected.
@router.get("/{customer_id}/relationships", response_model=list[CompanyIndividualRelationshipOut])
def list_customer_relationships(
    customer_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_module_access(MODULE, AccessLevel.VIEW)),
):
    customer = _customer_or_404(db, customer_id, current_user.company_id)
    rels = (
        db.query(CompanyIndividualRelationship)
        .filter(CompanyIndividualRelationship.from_customer_id == customer.id)
        .filter(CompanyIndividualRelationship.is_active)
        .order_by(CompanyIndividualRelationship.created_at.desc())
        .all()
    )
    return [_relationship_out(r) for r in rels]


@router.post("/{customer_id}/relationships", response_model=CompanyIndividualRelationshipOut)
def create_customer_relationship(
    customer_id: uuid.UUID,
    payload: CompanyIndividualRelationshipCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_module_access(MODULE, AccessLevel.EDIT)),
):
    customer = _customer_or_404(db, customer_id, current_user.company_id)
    if bool(payload.to_customer_id) == bool(payload.to_contact_id):
        raise HTTPException(
            status_code=422, detail="Link to exactly one of another Company/Individual or a Contact."
        )
    if payload.to_customer_id:
        target = _customer_or_404(db, payload.to_customer_id, current_user.company_id)
        if target.id == customer.id:
            raise HTTPException(status_code=422, detail="A record cannot be related to itself.")
    if payload.to_contact_id:
        _company_contact_or_404(db, payload.to_contact_id, current_user.company_id)

    rel = CompanyIndividualRelationship(
        company_id=current_user.company_id,
        from_customer_id=customer.id,
        to_customer_id=payload.to_customer_id,
        to_contact_id=payload.to_contact_id,
        relationship_type=payload.relationship_type,
        note=payload.note,
        created_by_user_id=current_user.id,
    )
    db.add(rel)
    db.flush()
    audit.record(
        db,
        entity_type="customer_relationship",
        entity_id=rel.id,
        action="created",
        actor_user_id=current_user.id,
        details=f"from={customer.name}, type={payload.relationship_type}",
        new_value={
            "to_customer_id": str(payload.to_customer_id) if payload.to_customer_id else None,
            "to_contact_id": str(payload.to_contact_id) if payload.to_contact_id else None,
            "relationship_type": payload.relationship_type,
        },
    )
    db.commit()
    db.refresh(rel)
    return _relationship_out(rel)


@router.post("/{customer_id}/relationships/{relationship_id}/deactivate", response_model=CompanyIndividualRelationshipOut)
def deactivate_customer_relationship(
    customer_id: uuid.UUID,
    relationship_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_module_access(MODULE, AccessLevel.EDIT)),
):
    customer = _customer_or_404(db, customer_id, current_user.company_id)
    rel = db.get(CompanyIndividualRelationship, relationship_id)
    if not rel or rel.from_customer_id != customer.id:
        raise HTTPException(status_code=404, detail="Relationship not found")
    rel.is_active = False
    audit.record(
        db,
        entity_type="customer_relationship",
        entity_id=rel.id,
        action="deactivated",
        actor_user_id=current_user.id,
        old_value={"is_active": True},
        new_value={"is_active": False},
    )
    db.commit()
    db.refresh(rel)
    return _relationship_out(rel)
