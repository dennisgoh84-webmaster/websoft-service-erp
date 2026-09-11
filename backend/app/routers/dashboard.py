"""
Summary dashboard -- the confirmed Service Operations Dashboard
Requirements from docs/business-requirements.md, as a single aggregated
endpoint so the frontend can render one overview screen.
"""
from datetime import date, timedelta
from decimal import Decimal

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
from app.services import ledger as ledger_svc
from app.services import reports as reports_svc

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

    # Every figure below is scoped to the company the user is currently
    # working in (multi-company) -- see app/routers/companies.py.
    excess_awaiting_review = (
        db.query(func.count(ExcessUsageRecord.id))
        .filter(
            ExcessUsageRecord.company_id == current_user.company_id,
            ExcessUsageRecord.treatment.is_(None),
        )
        .scalar()
        or 0
    )

    open_job_orders = (
        db.query(func.count(JobOrder.id))
        .filter(
            JobOrder.company_id == current_user.company_id,
            JobOrder.status.in_([JobOrderStatus.OPEN, JobOrderStatus.ASSIGNED]),
        )
        .scalar()
        or 0
    )

    # SRV-015: flagged missing/late if submitted more than 3 business days
    # after the work was performed. (Approximation -- see ServiceRecord.is_late;
    # detecting *never-submitted* work is future scope.)
    submitted_records = (
        db.query(ServiceRecord)
        .filter(
            ServiceRecord.company_id == current_user.company_id,
            ServiceRecord.status == ServiceRecordStatus.SUBMITTED,
        )
        .all()
    )
    missing_service_records = sum(1 for r in submitted_records if r.is_late)

    invoices = db.query(Invoice).filter(Invoice.company_id == current_user.company_id).all()
    invoices_total = float(sum(i.amount_sgd for i in invoices))

    # Financial summary -- same aging/trial-balance calculations as the
    # Accounting Reports screen (app/services/reports.py), just totalled.
    ar_rows = reports_svc.ar_aging_rows(db, current_user.company_id)
    ar_outstanding = sum((r["total"] for r in ar_rows), Decimal(0))
    ar_overdue = sum((r["total"] - r["current"] for r in ar_rows), Decimal(0))

    ap_rows = reports_svc.ap_aging_rows(db, current_user.company_id)
    ap_outstanding = sum((r["total"] for r in ap_rows), Decimal(0))
    ap_overdue = sum((r["total"] - r["current"] for r in ap_rows), Decimal(0))

    balances = ledger_svc.account_balances(db, current_user.company_id)
    total_debit = sum((row["debit_sgd"] for row in balances), Decimal(0))
    total_credit = sum((row["credit_sgd"] for row in balances), Decimal(0))
    gl_is_balanced = round(float(total_debit), 2) == round(float(total_credit), 2)

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
        ar_outstanding_sgd=float(ar_outstanding),
        ar_overdue_sgd=float(ar_overdue),
        ap_outstanding_sgd=float(ap_outstanding),
        ap_overdue_sgd=float(ap_overdue),
        gl_is_balanced=gl_is_balanced,
    )
