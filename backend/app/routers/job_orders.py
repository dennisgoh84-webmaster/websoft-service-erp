import uuid

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.models.core import User
from app.models.groups import AccessLevel
from app.models.job_orders import JobOrder, JobOrderStatus
from app.schemas.schemas import JobOrderAssign, JobOrderCreate, JobOrderOut, JobOrderSetDueDate
from app.services import audit
from app.services.authority import require_module_access

router = APIRouter(prefix="/api/job-orders", tags=["job-orders"])
MODULE = "service_operations"


@router.post("", response_model=JobOrderOut)
def create_job_order(
    payload: JobOrderCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_module_access(MODULE, AccessLevel.EDIT)),
):
    job_order = JobOrder(
        company_id=current_user.company_id,
        customer_id=payload.customer_id,
        contract_id=payload.contract_id,
        subject=payload.subject,
        priority=payload.priority,
        due_date=payload.due_date,
    )
    db.add(job_order)
    db.commit()
    db.refresh(job_order)
    return job_order


@router.get("", response_model=list[JobOrderOut])
def list_job_orders(
    status: JobOrderStatus | None = None,
    priority: str | None = None,
    customer_id: uuid.UUID | None = None,
    contract_id: uuid.UUID | None = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_module_access(MODULE, AccessLevel.VIEW)),
):
    query = db.query(JobOrder).filter(JobOrder.company_id == current_user.company_id)
    if status:
        query = query.filter(JobOrder.status == status)
    if priority:
        query = query.filter(JobOrder.priority == priority)
    if customer_id:
        query = query.filter(JobOrder.customer_id == customer_id)
    if contract_id:
        query = query.filter(JobOrder.contract_id == contract_id)
    return query.order_by(JobOrder.created_at.desc()).all()


@router.get("/{job_order_id}", response_model=JobOrderOut)
def get_job_order(
    job_order_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_module_access(MODULE, AccessLevel.VIEW)),
):
    job_order = db.get(JobOrder, job_order_id)
    if not job_order or job_order.company_id != current_user.company_id:
        raise HTTPException(status_code=404, detail="Job order not found")
    return job_order


@router.post("/{job_order_id}/assign", response_model=JobOrderOut)
def assign_job_order(
    job_order_id: uuid.UUID,
    payload: JobOrderAssign,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_module_access(MODULE, AccessLevel.EDIT)),
):
    job_order = db.get(JobOrder, job_order_id)
    if not job_order or job_order.company_id != current_user.company_id:
        raise HTTPException(status_code=404, detail="Job order not found")
    job_order.assigned_to_user_id = payload.assigned_to_user_id
    job_order.status = JobOrderStatus.ASSIGNED
    db.commit()
    db.refresh(job_order)
    return job_order


@router.post("/{job_order_id}/due-date", response_model=JobOrderOut)
def set_job_order_due_date(
    job_order_id: uuid.UUID,
    payload: JobOrderSetDueDate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_module_access(MODULE, AccessLevel.EDIT)),
):
    """Manual due date, set/changed by whoever opens the Job Order
    (Sales/Coordinator) after discussion with Support -- confirmed
    2026-09-10, see models/job_orders.py."""
    job_order = db.get(JobOrder, job_order_id)
    if not job_order or job_order.company_id != current_user.company_id:
        raise HTTPException(status_code=404, detail="Job order not found")
    old_due_date = job_order.due_date
    job_order.due_date = payload.due_date
    audit.record(
        db,
        entity_type="job_order",
        entity_id=job_order.id,
        action="due_date_set",
        actor_user_id=current_user.id,
        old_value={"due_date": old_due_date.isoformat() if old_due_date else None},
        new_value={"due_date": payload.due_date.isoformat() if payload.due_date else None},
    )
    db.commit()
    db.refresh(job_order)
    return job_order
