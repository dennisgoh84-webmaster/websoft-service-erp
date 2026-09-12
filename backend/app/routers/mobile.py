"""Mobile Web App API endpoints (planned-work.md #1).

Confirmed decisions (2026-09-12):
- Same login credentials, filtered to own assigned Job Orders only
- Time in/out replaces manual minutes (auto-computed)
- Camera-only + watermark for chop photo (no-reuse rule)
- Live connection assumed (no offline mode)
- Finger-drawn signature + typed name
- Photos + videos, no limit on count/size
"""
import math
import uuid
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.models.attachments import AttachmentKind, ServiceRecordAttachment, ServiceRecordSignoff
from app.models.company_individuals import CompanyIndividual
from app.models.contracts import HOUR_ROUNDING_MINUTES, Contract
from app.models.core import User
from app.models.groups import AccessLevel
from app.models.job_orders import JobOrder, JobOrderStatus
from app.models.service_records import (
    ServiceRecord,
    ServiceRecordCompletion,
    ServiceRecordOutcome,
    ServiceRecordStatus,
    round_up_to_nearest,
)
from app.services import audit
from app.services import file_storage
from app.services import service_records as service_record_svc
from app.services.authority import require_module_access
from app.services.numbering import next_document_number

router = APIRouter(prefix="/api/mobile", tags=["mobile"])
MODULE = "service_records"


# ── My assigned Job Orders ───────────────────────────────────────────

@router.get("/job-orders")
def my_job_orders(
    db: Session = Depends(get_db),
    current_user: User = Depends(require_module_access(MODULE, AccessLevel.VIEW)),
):
    """Job Orders assigned to the current user (OPEN or ASSIGNED only)."""
    orders = (
        db.query(JobOrder)
        .filter(
            JobOrder.company_id == current_user.company_id,
            JobOrder.assigned_to_user_id == current_user.id,
            JobOrder.status.in_([JobOrderStatus.OPEN, JobOrderStatus.ASSIGNED]),
        )
        .order_by(JobOrder.created_at.desc())
        .all()
    )
    result = []
    for jo in orders:
        customer = db.get(CompanyIndividual, jo.customer_id)
        contract = db.get(Contract, jo.contract_id) if jo.contract_id else None
        result.append({
            "id": str(jo.id),
            "job_order_number": jo.job_order_number,
            "subject": jo.subject,
            "status": jo.status.value,
            "priority": jo.priority.value,
            "is_urgent": jo.is_urgent,
            "customer_name": customer.name if customer else "",
            "contract_number": contract.contract_number if contract else None,
            "due_date": jo.due_date.isoformat() if jo.due_date else None,
            "created_at": jo.created_at.isoformat() if jo.created_at else None,
        })
    return result


@router.get("/job-orders/{job_order_id}")
def get_job_order_detail(
    job_order_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_module_access(MODULE, AccessLevel.VIEW)),
):
    """Full detail for one Job Order, including its Service Records."""
    jo = db.get(JobOrder, job_order_id)
    if not jo or jo.company_id != current_user.company_id:
        raise HTTPException(status_code=404, detail="Job Order not found")
    if jo.assigned_to_user_id != current_user.id:
        raise HTTPException(status_code=403, detail="This Job Order is not assigned to you")

    customer = db.get(CompanyIndividual, jo.customer_id)
    contract = db.get(Contract, jo.contract_id) if jo.contract_id else None

    records = (
        db.query(ServiceRecord)
        .filter(ServiceRecord.job_order_id == jo.id)
        .order_by(ServiceRecord.work_date.desc())
        .all()
    )

    sr_list = []
    for r in records:
        emp = db.get(User, r.employee_user_id)
        # Check for sign-off
        signoff = (
            db.query(ServiceRecordSignoff)
            .filter(ServiceRecordSignoff.service_record_id == r.id)
            .first()
        )
        # Count attachments
        att_count = (
            db.query(ServiceRecordAttachment)
            .filter(
                ServiceRecordAttachment.service_record_id == r.id,
                ServiceRecordAttachment.is_deleted == False,  # noqa: E712
            )
            .count()
        )
        sr_list.append({
            "id": str(r.id),
            "service_record_number": r.service_record_number,
            "work_date": r.work_date.isoformat(),
            "raw_minutes": r.raw_minutes,
            "rounded_minutes": r.rounded_minutes,
            "status": r.status.value,
            "outcome": r.outcome.value,
            "completion_status": r.completion_status.value,
            "is_after_hours": r.is_after_hours,
            "work_description": r.work_description,
            "time_in": r.time_in.isoformat() if r.time_in else None,
            "time_out": r.time_out.isoformat() if r.time_out else None,
            "employee_name": emp.full_name if emp else "",
            "has_signoff": signoff is not None,
            "attachment_count": att_count,
        })

    return {
        "id": str(jo.id),
        "job_order_number": jo.job_order_number,
        "subject": jo.subject,
        "status": jo.status.value,
        "priority": jo.priority.value,
        "is_urgent": jo.is_urgent,
        "customer_name": customer.name if customer else "",
        "contract_number": contract.contract_number if contract else None,
        "contract_remaining_minutes": contract.remaining_minutes if contract else None,
        "due_date": jo.due_date.isoformat() if jo.due_date else None,
        "service_records": sr_list,
    }


# ── Time In / Time Out ──────────────────────────────────────────────

@router.post("/job-orders/{job_order_id}/time-in")
def time_in(
    job_order_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_module_access(MODULE, AccessLevel.EDIT)),
):
    """Start a new Service Record with time_in = now. Returns the SR id."""
    jo = db.get(JobOrder, job_order_id)
    if not jo or jo.company_id != current_user.company_id:
        raise HTTPException(status_code=404, detail="Job Order not found")
    if jo.assigned_to_user_id != current_user.id:
        raise HTTPException(status_code=403, detail="This Job Order is not assigned to you")
    if jo.status in (JobOrderStatus.CLOSED, JobOrderStatus.VOID):
        raise HTTPException(status_code=422, detail="This Job Order is closed or voided")

    # Check no open (time_in set, time_out not set) record exists for this user on this JO
    open_sr = (
        db.query(ServiceRecord)
        .filter(
            ServiceRecord.job_order_id == jo.id,
            ServiceRecord.employee_user_id == current_user.id,
            ServiceRecord.time_in.isnot(None),
            ServiceRecord.time_out.is_(None),
        )
        .first()
    )
    if open_sr:
        raise HTTPException(
            status_code=422,
            detail=f"You already have an open time-in ({open_sr.service_record_number}). Tap Time Out first.",
        )

    now = datetime.now(timezone.utc)
    sr_number = next_document_number(db, "service_record", current_user.company_id)

    record = ServiceRecord(
        company_id=current_user.company_id,
        job_order_id=jo.id,
        employee_user_id=current_user.id,
        service_record_number=sr_number,
        work_date=now.date(),
        raw_minutes=0,
        rounded_minutes=0,
        time_in=now,
        status=ServiceRecordStatus.SUBMITTED,
        completion_status=ServiceRecordCompletion.UNCOMPLETED,
    )
    db.add(record)

    # Move JO to ASSIGNED if still OPEN
    if jo.status == JobOrderStatus.OPEN:
        jo.status = JobOrderStatus.ASSIGNED
        jo.assigned_to_user_id = current_user.id

    audit.record(
        db, entity_type="service_record", entity_id=record.id,
        action="time_in", actor_user_id=current_user.id,
        details=f"{sr_number} time-in at {now.isoformat()}",
    )
    db.commit()
    db.refresh(record)
    return {
        "id": str(record.id),
        "service_record_number": record.service_record_number,
        "time_in": record.time_in.isoformat(),
    }


@router.post("/service-records/{record_id}/time-out")
def time_out(
    record_id: uuid.UUID,
    completion_status: str = Form("U"),
    is_after_hours: bool = Form(False),
    work_description: str = Form(""),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_module_access(MODULE, AccessLevel.EDIT)),
):
    """Complete a Service Record: set time_out = now, compute minutes."""
    record = db.get(ServiceRecord, record_id)
    if not record or record.company_id != current_user.company_id:
        raise HTTPException(status_code=404, detail="Service Record not found")
    if record.employee_user_id != current_user.id:
        raise HTTPException(status_code=403, detail="This Service Record belongs to another staff member")
    if not record.time_in:
        raise HTTPException(status_code=422, detail="No time-in recorded for this Service Record")
    if record.time_out:
        raise HTTPException(status_code=422, detail="Time Out already recorded")

    now = datetime.now(timezone.utc)
    elapsed_seconds = (now - record.time_in).total_seconds()
    raw_minutes = max(1, math.ceil(elapsed_seconds / 60))
    rounded = round_up_to_nearest(raw_minutes, HOUR_ROUNDING_MINUTES)

    record.time_out = now
    record.raw_minutes = raw_minutes
    record.rounded_minutes = rounded
    record.is_after_hours = is_after_hours
    record.work_description = work_description.strip() or None

    cs = ServiceRecordCompletion.COMPLETED if completion_status == "C" else ServiceRecordCompletion.UNCOMPLETED
    record.completion_status = cs

    audit.record(
        db, entity_type="service_record", entity_id=record.id,
        action="time_out", actor_user_id=current_user.id,
        details=f"{record.service_record_number} time-out at {now.isoformat()}, {raw_minutes}min raw, {rounded}min rounded",
    )
    db.commit()
    db.refresh(record)
    return {
        "id": str(record.id),
        "service_record_number": record.service_record_number,
        "time_in": record.time_in.isoformat(),
        "time_out": record.time_out.isoformat(),
        "raw_minutes": record.raw_minutes,
        "rounded_minutes": record.rounded_minutes,
    }


# ── Attachments (photos / videos) ───────────────────────────────────

@router.post("/service-records/{record_id}/attachments")
async def upload_attachment(
    record_id: uuid.UUID,
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_module_access(MODULE, AccessLevel.EDIT)),
):
    """Upload a photo or video to a Service Record."""
    record = db.get(ServiceRecord, record_id)
    if not record or record.company_id != current_user.company_id:
        raise HTTPException(status_code=404, detail="Service Record not found")

    content_type = file.content_type or "application/octet-stream"
    if content_type.startswith("image/"):
        kind = AttachmentKind.WORK_PHOTO
    elif content_type.startswith("video/"):
        kind = AttachmentKind.WORK_VIDEO
    else:
        raise HTTPException(status_code=422, detail="Only photos and videos are accepted")

    data = await file.read()
    att_id = uuid.uuid4()
    stored_name = file_storage.save_file(
        company_id=current_user.company_id,
        service_record_id=record.id,
        attachment_id=att_id,
        original_filename=file.filename or "upload",
        data=data,
    )

    attachment = ServiceRecordAttachment(
        id=att_id,
        company_id=current_user.company_id,
        service_record_id=record.id,
        uploaded_by_user_id=current_user.id,
        kind=kind,
        original_filename=file.filename or "upload",
        stored_filename=stored_name,
        content_type=content_type,
        file_size_bytes=len(data),
    )
    db.add(attachment)

    audit.record(
        db, entity_type="service_record_attachment", entity_id=att_id,
        action="uploaded", actor_user_id=current_user.id,
        details=f"{file.filename} ({len(data)} bytes) on {record.service_record_number}",
    )
    db.commit()

    return {
        "id": str(att_id),
        "kind": kind.value,
        "original_filename": file.filename,
        "content_type": content_type,
        "file_size_bytes": len(data),
    }


@router.get("/service-records/{record_id}/attachments")
def list_attachments(
    record_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_module_access(MODULE, AccessLevel.VIEW)),
):
    """List all non-deleted attachments on a Service Record."""
    record = db.get(ServiceRecord, record_id)
    if not record or record.company_id != current_user.company_id:
        raise HTTPException(status_code=404, detail="Service Record not found")

    atts = (
        db.query(ServiceRecordAttachment)
        .filter(
            ServiceRecordAttachment.service_record_id == record.id,
            ServiceRecordAttachment.is_deleted == False,  # noqa: E712
        )
        .order_by(ServiceRecordAttachment.uploaded_at.asc())
        .all()
    )
    return [
        {
            "id": str(a.id),
            "kind": a.kind.value,
            "original_filename": a.original_filename,
            "content_type": a.content_type,
            "file_size_bytes": a.file_size_bytes,
            "uploaded_at": a.uploaded_at.isoformat() if a.uploaded_at else None,
        }
        for a in atts
    ]


@router.get("/attachments/{attachment_id}/file")
def download_attachment(
    attachment_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_module_access(MODULE, AccessLevel.VIEW)),
):
    """Serve the actual file bytes for an attachment."""
    att = db.get(ServiceRecordAttachment, attachment_id)
    if not att or att.company_id != current_user.company_id or att.is_deleted:
        raise HTTPException(status_code=404, detail="Attachment not found")

    path = file_storage.get_file_path(
        att.company_id, att.service_record_id, att.stored_filename
    )
    if not path:
        raise HTTPException(status_code=404, detail="File not found on disk")

    return FileResponse(
        path=str(path),
        media_type=att.content_type,
        filename=att.original_filename,
    )


@router.delete("/attachments/{attachment_id}")
def delete_attachment(
    attachment_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_module_access(MODULE, AccessLevel.EDIT)),
):
    """Soft-delete an attachment (never permanently removed)."""
    att = db.get(ServiceRecordAttachment, attachment_id)
    if not att or att.company_id != current_user.company_id:
        raise HTTPException(status_code=404, detail="Attachment not found")

    att.is_deleted = True
    audit.record(
        db, entity_type="service_record_attachment", entity_id=att.id,
        action="soft_deleted", actor_user_id=current_user.id,
        details=f"Deleted {att.original_filename} from SR {att.service_record_id}",
    )
    db.commit()
    return {"deleted": True}


# ── Sign-off (signature + chop photo) ───────────────────────────────

@router.post("/service-records/{record_id}/signoff")
async def create_signoff(
    record_id: uuid.UUID,
    signer_name: str = Form(...),
    signature_data_uri: str = Form(...),
    chop_photo: UploadFile = File(...),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_module_access(MODULE, AccessLevel.EDIT)),
):
    """Submit the customer sign-off: drawn signature + typed name + chop photo.

    The chop photo is auto-watermarked with the SR number + timestamp
    (camera-only + watermark, confirmed 2026-09-12)."""
    record = db.get(ServiceRecord, record_id)
    if not record or record.company_id != current_user.company_id:
        raise HTTPException(status_code=404, detail="Service Record not found")

    # Check for existing sign-off
    existing = (
        db.query(ServiceRecordSignoff)
        .filter(ServiceRecordSignoff.service_record_id == record.id)
        .first()
    )
    if existing:
        raise HTTPException(status_code=422, detail="This Service Record already has a sign-off")

    # Read and watermark the chop photo
    chop_data = await chop_photo.read()
    if not chop_data:
        raise HTTPException(status_code=422, detail="Chop photo is empty")

    now = datetime.now(timezone.utc)
    watermarked = file_storage.watermark_chop_photo(
        image_bytes=chop_data,
        service_record_number=record.service_record_number,
        timestamp=now,
    )

    # Save the watermarked chop as an attachment
    chop_att_id = uuid.uuid4()
    stored_name = file_storage.save_file(
        company_id=current_user.company_id,
        service_record_id=record.id,
        attachment_id=chop_att_id,
        original_filename="chop-photo.jpg",
        data=watermarked,
    )

    chop_attachment = ServiceRecordAttachment(
        id=chop_att_id,
        company_id=current_user.company_id,
        service_record_id=record.id,
        uploaded_by_user_id=current_user.id,
        kind=AttachmentKind.CHOP_PHOTO,
        original_filename="chop-photo.jpg",
        stored_filename=stored_name,
        content_type="image/jpeg",
        file_size_bytes=len(watermarked),
    )
    db.add(chop_attachment)

    # Create the sign-off record
    signoff = ServiceRecordSignoff(
        company_id=current_user.company_id,
        service_record_id=record.id,
        signer_name=signer_name.strip(),
        signature_data_uri=signature_data_uri,
        chop_attachment_id=chop_att_id,
        signed_by_user_id=current_user.id,
        signed_at=now,
    )
    db.add(signoff)

    audit.record(
        db, entity_type="service_record_signoff", entity_id=signoff.id,
        action="signed_off", actor_user_id=current_user.id,
        details=f"{record.service_record_number} signed by {signer_name.strip()} at {now.isoformat()}",
    )
    db.commit()

    return {
        "id": str(signoff.id),
        "signer_name": signoff.signer_name,
        "chop_attachment_id": str(chop_att_id),
        "signed_at": now.isoformat(),
    }


@router.get("/service-records/{record_id}/signoff")
def get_signoff(
    record_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_module_access(MODULE, AccessLevel.VIEW)),
):
    """Get the sign-off details for a Service Record (if exists)."""
    record = db.get(ServiceRecord, record_id)
    if not record or record.company_id != current_user.company_id:
        raise HTTPException(status_code=404, detail="Service Record not found")

    signoff = (
        db.query(ServiceRecordSignoff)
        .filter(ServiceRecordSignoff.service_record_id == record.id)
        .first()
    )
    if not signoff:
        return None

    return {
        "id": str(signoff.id),
        "signer_name": signoff.signer_name,
        "signature_data_uri": signoff.signature_data_uri,
        "chop_attachment_id": str(signoff.chop_attachment_id) if signoff.chop_attachment_id else None,
        "signed_at": signoff.signed_at.isoformat() if signoff.signed_at else None,
    }


# ── Open time-in check (for the mobile dashboard) ───────────────────

@router.get("/my-open-timein")
def my_open_timein(
    db: Session = Depends(get_db),
    current_user: User = Depends(require_module_access(MODULE, AccessLevel.VIEW)),
):
    """Check if the current user has any open time-in records."""
    open_sr = (
        db.query(ServiceRecord)
        .filter(
            ServiceRecord.company_id == current_user.company_id,
            ServiceRecord.employee_user_id == current_user.id,
            ServiceRecord.time_in.isnot(None),
            ServiceRecord.time_out.is_(None),
        )
        .first()
    )
    if not open_sr:
        return None

    jo = db.get(JobOrder, open_sr.job_order_id)
    return {
        "service_record_id": str(open_sr.id),
        "service_record_number": open_sr.service_record_number,
        "job_order_id": str(open_sr.job_order_id),
        "job_order_number": jo.job_order_number if jo else "",
        "job_order_subject": jo.subject if jo else "",
        "time_in": open_sr.time_in.isoformat(),
    }
