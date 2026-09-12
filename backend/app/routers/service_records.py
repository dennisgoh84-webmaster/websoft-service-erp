import uuid

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.models.core import Company, User
from app.models.company_individuals import CompanyIndividual
from app.models.groups import AccessLevel
from app.models.job_orders import JobOrder
from app.models.service_records import ServiceRecord, ServiceRecordStatus
from app.schemas.schemas import (
    PendingServiceRecordOut,
    ServiceRecordApprove,
    ServiceRecordCreate,
    ServiceRecordOut,
)
from app.services import audit, docx_forms, document_email, exports
from app.services import service_records as service_record_svc
from app.services.authority import require_module_access

router = APIRouter(prefix="/api/service-records", tags=["service-records"])
MODULE = "service_records"

SERVICE_RECORD_EXPORT_FIELDS = [
    "service_record_number", "job_order_subject", "employee_name", "work_date", "raw_minutes",
    "rounded_minutes", "deducted_minutes", "completion_status", "is_after_hours", "status", "outcome",
    "is_late",
]


@router.post("", response_model=ServiceRecordOut)
def submit_service_record(
    payload: ServiceRecordCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_module_access(MODULE, AccessLevel.EDIT)),
):
    try:
        record = service_record_svc.submit_service_record(
            db,
            job_order_id=payload.job_order_id,
            employee_user_id=payload.employee_user_id,
            work_date=payload.work_date,
            raw_minutes=payload.raw_minutes,
            completion_status=payload.completion_status,
            is_after_hours=payload.is_after_hours,
        )
    except service_record_svc.ContractRuleViolation as e:
        raise HTTPException(status_code=422, detail=str(e))
    db.commit()
    db.refresh(record)
    return record


@router.get("/pending-approval", response_model=list[PendingServiceRecordOut])
def list_pending_approvals(
    db: Session = Depends(get_db),
    current_user: User = Depends(require_module_access(MODULE, AccessLevel.FULL)),
):
    """Feeds the Service Record Approval page (below Service Records in
    the nav, confirmed 2026-09-11) -- every Submitted record across all
    Job Orders, oldest first, with everything the approver needs to key
    in a deduction without looking each thing up separately."""
    records = (
        db.query(ServiceRecord)
        .filter(ServiceRecord.company_id == current_user.company_id)
        .filter(ServiceRecord.status == ServiceRecordStatus.SUBMITTED)
        .order_by(ServiceRecord.submitted_at.asc())
        .all()
    )
    if not records:
        return []
    job_orders = {
        jo.id: jo
        for jo in db.query(JobOrder).filter(JobOrder.id.in_({r.job_order_id for r in records}))
    }
    employee_names = {
        u.id: u.full_name
        for u in db.query(User).filter(User.id.in_({r.employee_user_id for r in records}))
    }
    rows = []
    for r in records:
        jo = job_orders.get(r.job_order_id)
        contract = jo.contract if jo and jo.contract_id else None
        rows.append(
            PendingServiceRecordOut(
                id=r.id,
                service_record_number=r.service_record_number,
                job_order_id=r.job_order_id,
                job_order_number=jo.job_order_number if jo else "",
                job_order_subject=jo.subject if jo else "",
                is_urgent=jo.is_urgent if jo else False,
                employee_user_id=r.employee_user_id,
                employee_name=employee_names.get(r.employee_user_id, ""),
                work_date=r.work_date,
                raw_minutes=r.raw_minutes,
                rounded_minutes=r.rounded_minutes,
                completion_status=r.completion_status,
                is_after_hours=r.is_after_hours,
                suggested_deducted_minutes=service_record_svc.suggested_deduction_minutes(
                    rounded_minutes=r.rounded_minutes,
                    is_urgent=jo.is_urgent if jo else False,
                    is_after_hours=r.is_after_hours,
                ),
                contract_remaining_minutes=contract.remaining_minutes if contract else None,
                is_late=r.is_late,
            )
        )
    return rows


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


def _record_or_404(db: Session, record_id: uuid.UUID, company_id: uuid.UUID) -> ServiceRecord:
    r = db.get(ServiceRecord, record_id)
    if not r or r.company_id != company_id:
        raise HTTPException(status_code=404, detail="Service record not found")
    return r


def _service_record_row(r: ServiceRecord, job_order_subject: str, employee_name: str) -> dict:
    return {
        "service_record_number": r.service_record_number,
        "job_order_subject": job_order_subject,
        "employee_name": employee_name,
        "work_date": r.work_date.isoformat(),
        "raw_minutes": r.raw_minutes,
        "rounded_minutes": r.rounded_minutes,
        "deducted_minutes": r.deducted_minutes if r.deducted_minutes is not None else "",
        "completion_status": r.completion_status.value,
        "is_after_hours": r.is_after_hours,
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


@router.get("/{record_id}", response_model=ServiceRecordOut)
def get_service_record(
    record_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_module_access(MODULE, AccessLevel.VIEW)),
):
    return _record_or_404(db, record_id, current_user.company_id)


@router.get("/{record_id}/export.docx")
def export_service_record_docx(
    record_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_module_access(MODULE, AccessLevel.VIEW)),
):
    record = _record_or_404(db, record_id, current_user.company_id)
    job_order = db.get(JobOrder, record.job_order_id)
    customer = db.get(CompanyIndividual, job_order.customer_id) if job_order else None
    company = db.get(Company, current_user.company_id)
    data = docx_forms.service_record_to_docx(record, job_order, customer, company)
    return StreamingResponse(
        iter([data]),
        media_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        headers={"Content-Disposition": f"attachment; filename={record.service_record_number}.docx"},
    )


@router.post("/{record_id}/email")
def email_service_record(
    record_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_module_access(MODULE, AccessLevel.EDIT)),
):
    """Email Service Record (2026-09-12) -- same real-send pattern as
    Purchase Order's Email button. Goes to the customer on the Job
    Order this record was logged against."""
    record = _record_or_404(db, record_id, current_user.company_id)
    job_order = db.get(JobOrder, record.job_order_id)
    customer = db.get(CompanyIndividual, job_order.customer_id) if job_order else None
    if not customer or not customer.billing_email:
        raise HTTPException(
            status_code=422,
            detail="This customer has no email on file -- add one on the Company/Individual page first.",
        )
    company = db.get(Company, current_user.company_id)
    docx_bytes = docx_forms.service_record_to_docx(record, job_order, customer, company)
    body = (
        f"Dear {customer.name},\n\n"
        f"Please find attached Service Record {record.service_record_number} for Job Order "
        f"{job_order.job_order_number} ({job_order.subject}), dated {record.work_date.isoformat()}.\n\n"
        f"Regards,\n{company.name if company else ''}"
    )
    try:
        document_email.send_document_email(
            to_email=customer.billing_email,
            subject=f"Service Record {record.service_record_number} - {company.name if company else ''}",
            body_text=body,
            docx_bytes=docx_bytes,
            filename_stem=record.service_record_number,
        )
    except document_email.DocumentEmailError as e:
        raise HTTPException(status_code=e.status_code, detail=str(e))

    audit.record(
        db,
        entity_type="service_record",
        entity_id=record.id,
        action="emailed",
        actor_user_id=current_user.id,
        details=f"{record.service_record_number} emailed to {customer.billing_email}",
    )
    db.commit()
    return {"sent": True, "to": customer.billing_email}


@router.post("/{record_id}/approve", response_model=ServiceRecordOut)
def approve_service_record(
    record_id: uuid.UUID,
    payload: ServiceRecordApprove,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_module_access(MODULE, AccessLevel.FULL)),
):
    record = db.get(ServiceRecord, record_id)
    if not record or record.company_id != current_user.company_id:
        raise HTTPException(status_code=404, detail="Service record not found")
    job_order = db.get(JobOrder, record.job_order_id)
    try:
        service_record_svc.approve_service_record(
            db, record, job_order, approver=current_user, deducted_minutes=payload.deducted_minutes
        )
    except service_record_svc.ContractRuleViolation as e:
        raise HTTPException(status_code=422, detail=str(e))
    db.commit()
    db.refresh(record)
    return record
