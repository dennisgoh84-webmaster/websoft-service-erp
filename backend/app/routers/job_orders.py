import uuid

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.deps import get_current_user
from app.models.core import User
from app.models.job_orders import JobOrder, JobOrderStatus
from app.schemas.schemas import JobOrderAssign, JobOrderCreate, JobOrderOut

router = APIRouter(prefix="/api/job-orders", tags=["job-orders"])


@router.post("", response_model=JobOrderOut)
def create_job_order(
    payload: JobOrderCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    job_order = JobOrder(
        customer_id=payload.customer_id,
        contract_id=payload.contract_id,
        subject=payload.subject,
        priority=payload.priority,
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
    current_user: User = Depends(get_current_user),
):
    query = db.query(JobOrder)
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
    current_user: User = Depends(get_current_user),
):
    job_order = db.get(JobOrder, job_order_id)
    if not job_order:
        raise HTTPException(status_code=404, detail="Job order not found")
    return job_order


@router.post("/{job_order_id}/assign", response_model=JobOrderOut)
def assign_job_order(
    job_order_id: uuid.UUID,
    payload: JobOrderAssign,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    job_order = db.get(JobOrder, job_order_id)
    if not job_order:
        raise HTTPException(status_code=404, detail="Job order not found")
    job_order.assigned_to_user_id = payload.assigned_to_user_id
    job_order.status = JobOrderStatus.ASSIGNED
    db.commit()
    db.refresh(job_order)
    return job_order
