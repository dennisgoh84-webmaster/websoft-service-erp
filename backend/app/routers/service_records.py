import uuid

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.models.core import User
from app.models.groups import AccessLevel
from app.models.job_orders import JobOrder
from app.models.service_records import ServiceRecord
from app.schemas.schemas import ServiceRecordCreate, ServiceRecordOut
from app.services import exports
from app.services import service_records as service_record_svc
from app.services.authority import require_module_access

router = APIRouter(prefix="/api/service-records", tags=["service-records"])
MODULE = "service_records"

SERVICE_RECORD_EXPORT_FIELDS = [
    "service_record_number", "job_order_subject", "employee_name", "work_date", "raw_minutes",
    "rounded_minutes", "status", "outcome", "is_late",
]


@router.post("", response_model=ServiceRecordOut)
def submit_service_record(
    payload: ServiceRecordCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_module_access(MODULE, AccessLevel.EDIT)),
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


def _filter_service_records(
    db: Session,
    company_id: uuid.UUID,
    job_order_id: uuid.UUID | None,
    employee_user_id: uuid.UUID | None,
    status: str | None,
) -> list[ServiceRecord]:
    query = db.query(ServiceRecord).filter(ServiceRecord.company_id == company_id)
    if job_order_id:
        query = query.filter(ServiceRecord.job_order_id == job_order_id)
    if employee_user_id:
        query = query.filter(ServiceRecord.employee_user_id == employee_user_id)
    if status:
        query = query.filter(ServiceRecord.status == status)
    return query.order_by(ServiceRecord.work_date.desc()).all()


@router.get("", response_model=list[ServiceRecordOut])
def list_service_records(
    job_order_id: uuid.UUID | None = None,
    employee_user_id: uuid.UUID | None = None,
    status: str | None = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_module_access(MODULE, AccessLevel.VIEW)),
):
    return _filter_service_records(db, current_user.company_id, job_order_id, employee_user_id, status)


def _service_record_row(r: ServiceRecord, job_order_subject: str, employee_name: str) -> dict:
    return {
        "service_record_number": r.service_record_number,
        "job_order_subject": job_order_subject,
        "employee_name": employee_name,
        "work_date": r.work_date.isoformat(),
        "raw_minutes": r.raw_minutes,
        "rounded_minutes": r.rounded_minutes,
        "status": r.status.value,
        "outcome": r.outcome.value,
        "is_late": r.is_late,
    }


def _service_records_for_export(
    db: Session,
    company_id: uuid.UUID,
    job_order_id: uuid.UUID | None,
    employee_user_id: uuid.UUID | None,
    status: str | None,
) -> list[dict]:
    records = _filter_service_records(db, company_id, job_order_id, employee_user_id, status)
    job_order_subjects = {
        jo.id: jo.subject
        for jo in db.query(JobOrder).filter(JobOrder.id.in_({r.job_order_id for r in records}))
    } if records else {}
    employee_ids = {r.employee_user_id for r in records}
    employee_names = {u.id: u.full_name for u in db.query(User).filter(User.id.in_(employee_ids))} if employee_ids else {}
    return [
        _service_record_row(r, job_order_subjects.get(r.job_order_id, ""), employee_names.get(r.employee_user_id, ""))
        for r in records
    ]


@router.get("/export.csv")
def export_service_records_csv(
    job_order_id: uuid.UUID | None = None,
    employee_user_id: uuid.UUID | None = None,
    status: str | None = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_module_access(MODULE, AccessLevel.VIEW)),
):
    rows = _service_records_for_export(db, current_user.company_id, job_order_id, employee_user_id, status)
    csv_text = exports.rows_to_csv(SERVICE_RECORD_EXPORT_FIELDS, rows)
    return StreamingResponse(
        iter([csv_text]),
        media_type="text/csv",
        headers={"Content-Disposition": "attachment; filename=service-records.csv"},
    )


@router.get("/export.xlsx")
def export_service_records_excel(
    job_order_id: uuid.UUID | None = None,
    employee_user_id: uuid.UUID | None = None,
    status: str | None = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_module_access(MODULE, AccessLevel.VIEW)),
):
    rows = _service_records_for_export(db, current_user.company_id, job_order_id, employee_user_id, status)
    data = exports.rows_to_excel(SERVICE_RECORD_EXPORT_FIELDS, rows, sheet_name="Service Records")
    return StreamingResponse(
        iter([data]),
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": "attachment; filename=service-records.xlsx"},
    )


@router.post("/{record_id}/approve", response_model=ServiceRecordOut)
def approve_service_record(
    record_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_module_access(MODULE, AccessLevel.FULL)),
):
    record = db.get(ServiceRecord, record_id)
    if not record or record.company_id != current_user.company_id:
        raise HTTPException(status_code=404, detail="Service record not found")
    job_order = db.get(JobOrder, record.job_order_id)
    try:
        service_record_svc.approve_service_record(db, record, job_order, approver=current_user)
    except service_record_svc.ContractRuleViolation as e:
        raise HTTPException(status_code=422, detail=str(e))
    db.commit()
    db.refresh(record)
    return record
