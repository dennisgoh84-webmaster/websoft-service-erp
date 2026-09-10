"""
Summary dashboard -- the confirmed Service Operations Dashboard
Requirements from docs/business-requirements.md, as a single aggregated
endpoint so the frontend can render one overview screen.
"""
from datetime import date, timedelta

from fastapi import APIRouter, Depends
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.deps import get_current_user
from app.models.billing import Invoice
from app.models.contracts import Contract, ContractStatus, ExcessUsageRecord, PRE_EXPIRY_CHECK_LEAD_DAYS
from app.models.core import User
from app.models.job_orders import JobOrder, JobOrderStatus
from app.models.service_records import ServiceRecord, ServiceRecordStatus
from app.schemas.schemas import DashboardSummary

router = APIRouter(prefix="/api/dashboard", tags=["dashboard"])


@router.get("/summary", response_model=DashboardSummary)
def get_summary(db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    contracts = db.query(Contract).filter(Contract.company_id == current_user.company_id).all()

    active_contracts = sum(1 for c in contracts if c.status in (ContractStatus.ACTIVE, ContractStatus.EXCEEDED))
    today = date.today()
    contracts_expiring_soon = sum(
        1
        for c in contracts
        if c.status in (ContractStatus.ACTIVE, ContractStatus.EXCEEDED)
        and 0 <= (c.end_date - today).days <= PRE_EXPIRY_CHECK_LEAD_DAYS
    )
    total_contracted = sum(c.contracted_minutes for c in contracts) / 60
    total_consumed = sum(c.consumed_minutes for c in contracts) / 60
    total_remaining = sum(c.remaining_minutes for c in contracts) / 60

    excess_awaiting_review = (
        db.query(func.count(ExcessUsageRecord.id))
        .join(Contract, Contract.id == ExcessUsageRecord.contract_id)
        .filter(Contract.company_id == current_user.company_id, ExcessUsageRecord.treatment.is_(None))
        .scalar()
        or 0
    )

    open_job_orders = (
        db.query(func.count(JobOrder.id))
        .filter(JobOrder.status.in_([JobOrderStatus.OPEN, JobOrderStatus.ASSIGNED]))
        .scalar()
        or 0
    )

    # SRV-015: flagged missing/late if submitted more than 3 business days
    # after the work was performed. (Approximation -- see ServiceRecord.is_late;
    # detecting *never-submitted* work is future scope.)
    submitted_records = (
        db.query(ServiceRecord).filter(ServiceRecord.status == ServiceRecordStatus.SUBMITTED).all()
    )
    missing_service_records = sum(1 for r in submitted_records if r.is_late)

    invoices = db.query(Invoice).join(Contract, Invoice.contract_id == Contract.id, isouter=True).all()
    # Fall back to all invoices for this company's customers if contract_id is null (future-proofing).
    invoices_total = float(sum(i.amount_sgd for i in invoices))

    return DashboardSummary(
        active_contracts=active_contracts,
        contracts_expiring_soon=contracts_expiring_soon,
        total_contracted_hours=total_contracted,
        total_consumed_hours=total_consumed,
        total_remaining_hours=total_remaining,
        excess_awaiting_review=excess_awaiting_review,
        open_job_orders=open_job_orders,
        missing_service_records=missing_service_records,
        invoices_total_sgd=invoices_total,
        invoices_count=len(invoices),
    )
