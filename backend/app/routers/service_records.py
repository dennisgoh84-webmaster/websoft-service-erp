import uuid

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.deps import get_current_user
from app.models.core import User
from app.models.job_orders import JobOrder
from app.models.service_records import ServiceRecord
from app.schemas.schemas import ServiceRecordCreate, ServiceRecordOut
from app.services import service_records as service_record_svc

router = APIRouter(prefix="/api/service-records", tags=["service-records"])


@router.post("", response_model=ServiceRecordOut)
def submit_service_record(
    payload: ServiceRecordCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    record = service_record_svc.submit_service_record(
        db,
        job_order_id=payload.job_order_id,
        employee_user_id=payload.employee_user_id,
        work_date=payload.work_date,
        raw_minutes=payload.raw_minutes,
    )
    db.commit()
    db.refresh(record)
    return record


@router.get("", response_model=list[ServiceRecordOut])
def list_service_records(
    job_order_id: uuid.UUID | None = None,
    employee_user_id: uuid.UUID | None = None,
    status: str | None = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    query = db.query(ServiceRecord)
    if job_order_id:
        query = query.filter(ServiceRecord.job_order_id == job_order_id)
    if employee_user_id:
        query = query.filter(ServiceRecord.employee_user_id == employee_user_id)
    if status:
        query = query.filter(ServiceRecord.status == status)
    return query.order_by(ServiceRecord.work_date.desc()).all()


@router.post("/{record_id}/approve", response_model=ServiceRecordOut)
def approve_service_record(
    record_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    record = db.get(ServiceRecord, record_id)
    if not record:
        raise HTTPException(status_code=404, detail="Service record not found")
    job_order = db.get(JobOrder, record.job_order_id)
    try:
        service_record_svc.approve_service_record(db, record, job_order, approver=current_user)
    except service_record_svc.ContractRuleViolation as e:
        raise HTTPException(status_code=422, detail=str(e))
    db.commit()
    db.refresh(record)
    return record
