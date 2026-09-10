import uuid

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.models.core import User
from app.models.customers import Customer
from app.models.groups import AccessLevel
from app.models.job_orders import JobOrder, JobOrderStatus
from app.schemas.schemas import JobOrderAssign, JobOrderCreate, JobOrderOut, JobOrderSetDueDate
from app.services import audit, exports
from app.services.authority import require_module_access

router = APIRouter(prefix="/api/job-orders", tags=["job-orders"])
MODULE = "service_operations"

JOB_ORDER_EXPORT_FIELDS = [
    "subject", "customer_name", "priority", "status", "assigned_to", "due_date", "created_at",
]


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


def _filter_job_orders(
    db: Session,
    company_id: uuid.UUID,
    status: JobOrderStatus | None,
    priority: str | None,
    customer_id: uuid.UUID | None,
    contract_id: uuid.UUID | None,
) -> list[JobOrder]:
    query = db.query(JobOrder).filter(JobOrder.company_id == company_id)
    if status:
        query = query.filter(JobOrder.status == status)
    if priority:
        query = query.filter(JobOrder.priority == priority)
    if customer_id:
        query = query.filter(JobOrder.customer_id == customer_id)
    if contract_id:
        query = query.filter(JobOrder.contract_id == contract_id)
    return query.order_by(JobOrder.created_at.desc()).all()


@router.get("", response_model=list[JobOrderOut])
def list_job_orders(
    status: JobOrderStatus | None = None,
    priority: str | None = None,
    customer_id: uuid.UUID | None = None,
    contract_id: uuid.UUID | None = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_module_access(MODULE, AccessLevel.VIEW)),
):
    return _filter_job_orders(db, current_user.company_id, status, priority, customer_id, contract_id)


def _job_order_row(jo: JobOrder, customer_name: str, assigned_name: str) -> dict:
    return {
        "subject": jo.subject,
        "customer_name": customer_name,
        "priority": jo.priority.value,
        "status": jo.status.value,
        "assigned_to": assigned_name,
        "due_date": jo.due_date.isoformat() if jo.due_date else "",
        "created_at": jo.created_at.isoformat(),
    }


def _job_orders_for_export(
    db: Session,
    company_id: uuid.UUID,
    status: JobOrderStatus | None,
    priority: str | None,
    customer_id: uuid.UUID | None,
    contract_id: uuid.UUID | None,
) -> list[dict]:
    job_orders = _filter_job_orders(db, company_id, status, priority, customer_id, contract_id)
    customer_names = {c.id: c.name for c in db.query(Customer).filter(Customer.company_id == company_id)}
    # Looked up by the exact ids referenced, not "users in this company" --
    # a user's User.company_id is only their *current* company (see
    # models/core.py), so a staff member since switched elsewhere would
    # otherwise go missing from a company they're still assigned work in.
    assignee_ids = {jo.assigned_to_user_id for jo in job_orders if jo.assigned_to_user_id}
    user_names = {u.id: u.full_name for u in db.query(User).filter(User.id.in_(assignee_ids))} if assignee_ids else {}
    return [
        _job_order_row(
            jo,
            customer_names.get(jo.customer_id, ""),
            user_names.get(jo.assigned_to_user_id, "") if jo.assigned_to_user_id else "",
        )
        for jo in job_orders
    ]


@router.get("/export.csv")
def export_job_orders_csv(
    status: JobOrderStatus | None = None,
    priority: str | None = None,
    customer_id: uuid.UUID | None = None,
    contract_id: uuid.UUID | None = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_module_access(MODULE, AccessLevel.VIEW)),
):
    rows = _job_orders_for_export(db, current_user.company_id, status, priority, customer_id, contract_id)
    csv_text = exports.rows_to_csv(JOB_ORDER_EXPORT_FIELDS, rows)
    return StreamingResponse(
        iter([csv_text]),
        media_type="text/csv",
        headers={"Content-Disposition": "attachment; filename=job-orders.csv"},
    )


@router.get("/export.xlsx")
def export_job_orders_excel(
    status: JobOrderStatus | None = None,
    priority: str | None = None,
    customer_id: uuid.UUID | None = None,
    contract_id: uuid.UUID | None = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_module_access(MODULE, AccessLevel.VIEW)),
):
    rows = _job_orders_for_export(db, current_user.company_id, status, priority, customer_id, contract_id)
    data = exports.rows_to_excel(JOB_ORDER_EXPORT_FIELDS, rows, sheet_name="Job Orders")
    return StreamingResponse(
        iter([data]),
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": "attachment; filename=job-orders.xlsx"},
    )


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
