"""Customer Groups -- a lightweight tag linking separate Customer
records that belong to the same group of companies. See
app/models/customers.py's CustomerGroup docstring: each tagged
customer stays its own full account (own contracts/invoices/AR); this
is deliberately not a merged/consolidated-billing hierarchy. Confirmed
2026-09-10."""
import uuid

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.models.core import User
from app.models.customers import CustomerGroup
from app.models.groups import AccessLevel
from app.schemas.schemas import CustomerGroupCreate, CustomerGroupOut, CustomerGroupUpdate
from app.services import audit
from app.services.authority import require_module_access

router = APIRouter(prefix="/api/customer-groups", tags=["customer-groups"])
MODULE = "customer_management"


def _group_or_404(db: Session, group_id: uuid.UUID, company_id: uuid.UUID) -> CustomerGroup:
    group = db.get(CustomerGroup, group_id)
    if not group or group.company_id != company_id:
        raise HTTPException(status_code=404, detail="Customer group not found")
    return group


@router.get("", response_model=list[CustomerGroupOut])
def list_customer_groups(
    include_inactive: bool = False,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_module_access(MODULE, AccessLevel.VIEW)),
):
    query = db.query(CustomerGroup).filter(CustomerGroup.company_id == current_user.company_id)
    if not include_inactive:
        query = query.filter(CustomerGroup.is_active)
    return query.order_by(CustomerGroup.name).all()


@router.post("", response_model=CustomerGroupOut)
def create_customer_group(
    payload: CustomerGroupCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_module_access(MODULE, AccessLevel.EDIT)),
):
    group = CustomerGroup(company_id=current_user.company_id, name=payload.name, description=payload.description)
    db.add(group)
    db.flush()
    audit.record(
        db,
        entity_type="customer_group",
        entity_id=group.id,
        action="created",
        actor_user_id=current_user.id,
        details=f"name={payload.name}",
        new_value={"name": payload.name},
    )
    db.commit()
    db.refresh(group)
    return group


@router.patch("/{group_id}", response_model=CustomerGroupOut)
def update_customer_group(
    group_id: uuid.UUID,
    payload: CustomerGroupUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_module_access(MODULE, AccessLevel.EDIT)),
):
    group = _group_or_404(db, group_id, current_user.company_id)
    fields = payload.model_dump(exclude_unset=True)
    old_value: dict[str, object] = {}
    new_value: dict[str, object] = {}
    for field in ("name", "description", "is_active"):
        if field not in fields or getattr(group, field) == fields[field]:
            continue
        old_value[field] = getattr(group, field)
        new_value[field] = fields[field]
        setattr(group, field, fields[field])

    audit.record(
        db,
        entity_type="customer_group",
        entity_id=group.id,
        action="updated",
        actor_user_id=current_user.id,
        old_value=old_value or None,
        new_value=new_value or None,
    )
    db.commit()
    db.refresh(group)
    return group
