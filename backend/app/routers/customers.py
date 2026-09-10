import uuid

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.models.core import AuditLogEntry, User
from app.models.customers import Contact, Customer
from app.models.groups import AccessLevel
from app.schemas.schemas import (
    AuditLogEntryOut,
    ContactCreate,
    ContactOut,
    ContactUpdate,
    CustomerCreate,
    CustomerOut,
    CustomerUpdate,
)
from app.services import audit
from app.services.authority import require_module_access

router = APIRouter(prefix="/api/customers", tags=["customers"])
MODULE = "customer_management"

CUSTOMER_FIELDS = (
    "customer_type",
    "name",
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
    "exclude_auto_sent",
    "terms_and_conditions",
    "payment_terms_days",
)


def _customer_or_404(db: Session, customer_id: uuid.UUID, company_id: uuid.UUID) -> Customer:
    customer = db.get(Customer, customer_id)
    # Multi-company: another company's customer is "not found" here.
    if not customer or customer.company_id != company_id:
        raise HTTPException(status_code=404, detail="Customer not found")
    return customer


def _contact_or_404(db: Session, customer: Customer, contact_id: uuid.UUID) -> Contact:
    contact = db.get(Contact, contact_id)
    if not contact or contact.customer_id != customer.id:
        raise HTTPException(status_code=404, detail="Contact not found")
    return contact


@router.post("", response_model=CustomerOut)
def create_customer(
    payload: CustomerCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_module_access(MODULE, AccessLevel.EDIT)),
):
    fields = payload.model_dump()
    customer = Customer(company_id=current_user.company_id, **fields)
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


@router.patch("/{customer_id}", response_model=CustomerOut)
def update_customer(
    customer_id: uuid.UUID,
    payload: CustomerUpdate,
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


@router.post("/{customer_id}/deactivate", response_model=CustomerOut)
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


@router.post("/{customer_id}/reactivate", response_model=CustomerOut)
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


@router.get("", response_model=list[CustomerOut])
def list_customers(
    db: Session = Depends(get_db),
    current_user: User = Depends(require_module_access(MODULE, AccessLevel.VIEW)),
):
    return db.query(Customer).filter(Customer.company_id == current_user.company_id).all()


@router.get("/{customer_id}", response_model=CustomerOut)
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
    """Recent Customer Management activity for this account (created,
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
# same customer_management module authority.


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
    contact = Contact(customer_id=customer.id, name=payload.name, email=payload.email, phone=payload.phone)
    db.add(contact)
    db.flush()
    audit.record(
        db,
        entity_type="contact",
        entity_id=contact.id,
        action="created",
        actor_user_id=current_user.id,
        details=f"customer={customer.name}, name={payload.name}",
        new_value={"name": payload.name, "email": payload.email, "phone": payload.phone},
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
    for field in ("name", "email", "phone"):
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
