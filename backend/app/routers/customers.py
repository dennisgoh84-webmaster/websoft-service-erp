import uuid

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.models.core import User
from app.models.customers import Customer
from app.models.groups import AccessLevel
from app.schemas.schemas import CustomerCreate, CustomerOut, CustomerUpdate
from app.services import audit
from app.services.authority import require_module_access

router = APIRouter(prefix="/api/customers", tags=["customers"])
MODULE = "customer_management"


@router.post("", response_model=CustomerOut)
def create_customer(
    payload: CustomerCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_module_access(MODULE, AccessLevel.EDIT)),
):
    customer = Customer(
        company_id=current_user.company_id,
        name=payload.name,
        billing_email=payload.billing_email,
        billing_address=payload.billing_address,
        payment_terms_days=payload.payment_terms_days,
    )
    db.add(customer)
    db.flush()
    audit.record(
        db,
        entity_type="customer",
        entity_id=customer.id,
        action="created",
        actor_user_id=current_user.id,
        details=f"name={payload.name}",
        new_value={
            "name": payload.name,
            "billing_email": payload.billing_email,
            "payment_terms_days": payload.payment_terms_days,
        },
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
    customer = db.get(Customer, customer_id)
    if not customer or customer.company_id != current_user.company_id:
        raise HTTPException(status_code=404, detail="Customer not found")

    fields = payload.model_dump(exclude_unset=True)
    old_value: dict[str, object] = {}
    new_value: dict[str, object] = {}
    for field in ("name", "billing_email", "billing_address", "payment_terms_days"):
        if field not in fields:
            continue
        old = getattr(customer, field)
        if old == fields[field]:
            continue
        old_value[field] = old
        new_value[field] = fields[field]
        setattr(customer, field, fields[field])

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
    customer = db.get(Customer, customer_id)
    # Multi-company: another company's customer is "not found" here.
    if not customer or customer.company_id != current_user.company_id:
        raise HTTPException(status_code=404, detail="Customer not found")
    return customer
