"""CompanyIndividual Groups -- a lightweight tag linking separate CompanyIndividual
records that belong to the same group of companies. See
app/models/company_individuals.py's CompanyIndividualGroup docstring: each tagged
customer stays its own full account (own contracts/invoices/AR); this
is deliberately not a merged/consolidated-billing hierarchy. Confirmed
2026-09-10."""
import uuid

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.models.core import User
from app.models.company_individuals import CompanyIndividualGroup
from app.models.groups import AccessLevel
from app.schemas.schemas import CompanyIndividualGroupCreate, CompanyIndividualGroupOut, CompanyIndividualGroupUpdate
from app.services import audit
from app.services.authority import require_module_access

router = APIRouter(prefix="/api/company-individual-groups", tags=["company-individual-groups"])
MODULE = "company_individual_management"


def _group_or_404(db: Session, group_id: uuid.UUID, company_id: uuid.UUID) -> CompanyIndividualGroup:
    group = db.get(CompanyIndividualGroup, group_id)
    if not group or group.company_id != company_id:
        raise HTTPException(status_code=404, detail="Company / Individual group not found")
    return group


@router.get("", response_model=list[CompanyIndividualGroupOut])
def list_customer_groups(
    include_inactive: bool = False,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_module_access(MODULE, AccessLevel.VIEW)),
):
    query = db.query(CompanyIndividualGroup).filter(CompanyIndividualGroup.company_id == current_user.company_id)
    if not include_inactive:
        query = query.filter(CompanyIndividualGroup.is_active)
    return query.order_by(CompanyIndividualGroup.name).all()


@router.post("", response_model=CompanyIndividualGroupOut)
def create_customer_group(
    payload: CompanyIndividualGroupCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_module_access(MODULE, AccessLevel.EDIT)),
):
    group = CompanyIndividualGroup(company_id=current_user.company_id, name=payload.name, description=payload.description)
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


@router.patch("/{group_id}", response_model=CompanyIndividualGroupOut)
def update_customer_group(
    group_id: uuid.UUID,
    payload: CompanyIndividualGroupUpdate,
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
