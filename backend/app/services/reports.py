"""
Read-only reporting queries behind the Operations Reports and
Accounting Reports screens (module_keys "operations_reports" /
"accounting_reports" -- see app/routers/reports.py).

Every function here only *filters and reads* data that another module
already owns and has already computed the rules for (contract hours,
GST, aging buckets, the trial balance) -- no new business rule is
introduced in this file. The AR/AP aging bucketing in particular is a
line-for-line copy of the loop in app/routers/accounts_receivable.py's
aging_report and app/routers/payables.py's ap_aging, kept here as a
plain function (rather than importing the FastAPI route) so both the
Accounting Reports screen and the Company Dashboard summary can reuse
the exact same figures without diverging.
"""
import uuid
from datetime import date
from decimal import Decimal

from sqlalchemy.orm import Session

from app.models.billing import Invoice, InvoiceStatus
from app.models.catalog import Product
from app.models.contracts import Contract, ContractKind, ContractProduct, ContractStatus
from app.models.company_individuals import CompanyIndividual
from app.models.job_orders import JobOrder, JobOrderStatus
from app.models.company_individuals import CompanyIndividual
from app.models.payables import BillStatus, SupplierInvoice
from app.models.payments import CommissionSettings, PaymentAllocation
from app.models.service_records import ServiceRecord, ServiceRecordOutcome, ServiceRecordStatus
from app.models.setup import SetupListItem, SetupListType
from app.services.accounts_receivable import aging_bucket_for

EMPTY_BUCKET = {
    "current": Decimal(0),
    "1_30": Decimal(0),
    "31_60": Decimal(0),
    "61_90": Decimal(0),
    "over_90": Decimal(0),
}


# ---- Operations Reports ----------------------------------------------


def list_contracts_report(
    db: Session,
    company_id: uuid.UUID,
    *,
    status: ContractStatus | None = None,
    contract_kind: ContractKind | None = None,
    customer_id: uuid.UUID | None = None,
    expiring_within_days: int | None = None,
    start_date: date | None = None,
    end_date: date | None = None,
) -> list[Contract]:
    query = db.query(Contract).filter(Contract.company_id == company_id)
    if status is not None:
        query = query.filter(Contract.status == status)
    if contract_kind is not None:
        query = query.filter(Contract.contract_kind == contract_kind)
    if customer_id is not None:
        query = query.filter(Contract.customer_id == customer_id)
    if start_date is not None:
        query = query.filter(Contract.end_date >= start_date)
    if end_date is not None:
        query = query.filter(Contract.start_date <= end_date)
    contracts = query.order_by(Contract.end_date).all()
    if expiring_within_days is not None:
        today = date.today()
        contracts = [c for c in contracts if 0 <= (c.end_date - today).days <= expiring_within_days]
    return contracts


def list_job_orders_report(
    db: Session,
    company_id: uuid.UUID,
    *,
    status: JobOrderStatus | None = None,
    customer_id: uuid.UUID | None = None,
    assigned_to_user_id: uuid.UUID | None = None,
    overdue_only: bool = False,
    start_date: date | None = None,
    end_date: date | None = None,
) -> list[JobOrder]:
    query = db.query(JobOrder).filter(JobOrder.company_id == company_id)
    if status is not None:
        query = query.filter(JobOrder.status == status)
    if customer_id is not None:
        query = query.filter(JobOrder.customer_id == customer_id)
    if assigned_to_user_id is not None:
        query = query.filter(JobOrder.assigned_to_user_id == assigned_to_user_id)
    if start_date is not None:
        query = query.filter(JobOrder.created_at >= start_date)
    if end_date is not None:
        query = query.filter(JobOrder.created_at <= end_date)
    orders = query.order_by(JobOrder.created_at.desc()).all()
    if overdue_only:
        today = date.today()
        orders = [
            o
            for o in orders
            if o.due_date
            and o.due_date < today
            and o.status not in (JobOrderStatus.CLOSED, JobOrderStatus.VOID)
        ]
    return orders


def list_service_records_report(
    db: Session,
    company_id: uuid.UUID,
    *,
    status: ServiceRecordStatus | None = None,
    outcome: ServiceRecordOutcome | None = None,
    customer_id: uuid.UUID | None = None,
    employee_user_id: uuid.UUID | None = None,
    start_date: date | None = None,
    end_date: date | None = None,
) -> list[ServiceRecord]:
    query = (
        db.query(ServiceRecord)
        .join(JobOrder, JobOrder.id == ServiceRecord.job_order_id)
        .filter(ServiceRecord.company_id == company_id)
    )
    if status is not None:
        query = query.filter(ServiceRecord.status == status)
    if outcome is not None:
        query = query.filter(ServiceRecord.outcome == outcome)
    if customer_id is not None:
        query = query.filter(JobOrder.customer_id == customer_id)
    if employee_user_id is not None:
        query = query.filter(ServiceRecord.employee_user_id == employee_user_id)
    if start_date is not None:
        query = query.filter(ServiceRecord.work_date >= start_date)
    if end_date is not None:
        query = query.filter(ServiceRecord.work_date <= end_date)
    return query.order_by(ServiceRecord.work_date.desc()).all()


def list_customer_product_usage(
    db: Session,
    company_id: uuid.UUID,
    *,
    customer_id: uuid.UUID | None = None,
    product_id: uuid.UUID | None = None,
    industry_code: str | None = None,
) -> list[dict]:
    """Confirmed 2026-09-11: "check customer using which product" --
    one row per (customer, product) currently covered under a
    contract's Product Coverage (ContractProduct). Filter by CompanyIndividual
    to see everything they have; filter by Product to see who has it
    (and, by comparison against the full customer list, who doesn't)
    -- the starting point for a manual add-on/renewal conversation.
    Visibility only, confirmed in scope for this round -- no automated
    "gap" flagging or renewal reminders yet (separate, not-yet-scoped
    follow-up)."""
    query = (
        db.query(Contract, CompanyIndividual, Product)
        .join(ContractProduct, ContractProduct.contract_id == Contract.id)
        .join(CompanyIndividual, Contract.customer_id == CompanyIndividual.id)
        .join(Product, ContractProduct.product_id == Product.id)
        .filter(Contract.company_id == company_id)
    )
    if customer_id is not None:
        query = query.filter(CompanyIndividual.id == customer_id)
    if product_id is not None:
        query = query.filter(Product.id == product_id)
    if industry_code is not None:
        query = query.filter(CompanyIndividual.industry_code == industry_code)
    rows = query.order_by(CompanyIndividual.name, Product.name).all()

    industry_names = {
        i.code: i.name
        for i in db.query(SetupListItem).filter(SetupListItem.list_type == SetupListType.INDUSTRY)
    }

    return [
        {
            "customer_id": customer.id,
            "customer_name": customer.name,
            "industry_code": customer.industry_code,
            "industry_name": industry_names.get(customer.industry_code, ""),
            "product_id": product.id,
            "product_name": product.name,
            "contract_id": contract.id,
            "contract_number": contract.contract_number,
            "contract_kind": contract.contract_kind.value,
            "contract_status": contract.status.value,
            "start_date": contract.start_date,
            "end_date": contract.end_date,
        }
        for contract, customer, product in rows
    ]


# ---- Accounting Reports ------------------------------------------------


def ar_aging_rows(db: Session, company_id: uuid.UUID, as_at: date | None = None) -> list[dict]:
    """Same bucketing as accounts_receivable.aging_report (AR-003:
    disputed invoices are included, not excluded from collections)."""
    as_at = as_at or date.today()
    invoices = (
        db.query(Invoice)
        .filter(
            Invoice.company_id == company_id,
            Invoice.status != InvoiceStatus.PAID,
            Invoice.status != InvoiceStatus.WRITTEN_OFF,
        )
        .all()
    )
    customers = {c.id: c.name for c in db.query(CompanyIndividual).filter(CompanyIndividual.company_id == company_id)}

    buckets: dict[uuid.UUID, dict[str, Decimal]] = {}
    for invoice in invoices:
        outstanding = invoice.outstanding_sgd
        if outstanding <= 0:
            continue
        row = buckets.setdefault(invoice.customer_id, dict(EMPTY_BUCKET))
        row[aging_bucket_for(invoice.due_date, as_at)] += outstanding

    rows = [
        {
            "customer_id": cid,
            "customer_name": customers.get(cid, "(unknown)"),
            "current": b["current"],
            "days_1_30": b["1_30"],
            "days_31_60": b["31_60"],
            "days_61_90": b["61_90"],
            "over_90": b["over_90"],
            "total": sum(b.values()),
        }
        for cid, b in buckets.items()
    ]
    rows.sort(key=lambda r: r["total"], reverse=True)
    return rows


def ap_aging_rows(db: Session, company_id: uuid.UUID, as_at: date | None = None) -> list[dict]:
    """Same bucketing as payables.ap_aging."""
    as_at = as_at or date.today()
    bills = (
        db.query(SupplierInvoice)
        .filter(SupplierInvoice.company_id == company_id, SupplierInvoice.status != BillStatus.PAID)
        .all()
    )
    suppliers = {s.id: s.name for s in db.query(CompanyIndividual).filter(CompanyIndividual.company_id == company_id)}

    buckets: dict[uuid.UUID, dict[str, Decimal]] = {}
    for bill in bills:
        outstanding = bill.outstanding_sgd
        if outstanding <= 0:
            continue
        row = buckets.setdefault(bill.supplier_id, dict(EMPTY_BUCKET))
        row[aging_bucket_for(bill.due_date, as_at)] += outstanding

    rows = [
        {
            "supplier_id": sid,
            "supplier_name": suppliers.get(sid, "(unknown)"),
            "current": b["current"],
            "days_1_30": b["1_30"],
            "days_31_60": b["31_60"],
            "days_61_90": b["61_90"],
            "over_90": b["over_90"],
            "total": sum(b.values()),
        }
        for sid, b in buckets.items()
    ]
    rows.sort(key=lambda r: r["total"], reverse=True)
    return rows


# ---- GST Return (Analysis) ----------------------------------------------


def gst_return_data(
    db: Session, company_id: uuid.UUID, period_start: date, period_end: date
) -> dict:
    """Output tax (sales, by tax code) vs input tax (purchases) for a
    date range, tax point = invoice date (confirmed default -- see
    docs/open-business-decisions.md; bad-debt relief on written-off
    invoices is a separate IRAS scheme this does not attempt). Purely a
    read-only total: this does not file anything or post to the GL."""
    invoices = (
        db.query(Invoice)
        .filter(
            Invoice.company_id == company_id,
            Invoice.issued_at >= period_start,
            Invoice.issued_at <= period_end,
        )
        .all()
    )
    output_by_code: dict[str, dict] = {}
    for inv in invoices:
        row = output_by_code.setdefault(
            inv.tax_code, {"net": Decimal("0.00"), "tax": Decimal("0.00"), "count": 0}
        )
        row["net"] += Decimal(inv.amount_sgd)
        row["tax"] += Decimal(inv.gst_amount_sgd)
        row["count"] += 1

    bills = (
        db.query(SupplierInvoice)
        .filter(
            SupplierInvoice.company_id == company_id,
            SupplierInvoice.invoice_date >= period_start,
            SupplierInvoice.invoice_date <= period_end,
        )
        .all()
    )
    # SupplierInvoice doesn't carry a tax_code (see app/models/payables.py)
    # -- input tax is tracked as one total, not broken out per code.
    input_row = {"net": Decimal("0.00"), "tax": Decimal("0.00"), "count": 0}
    for bill in bills:
        input_row["net"] += Decimal(bill.amount_sgd)
        input_row["tax"] += Decimal(bill.gst_amount_sgd)
        input_row["count"] += 1

    output_rows = [
        {"tax_code": code, "net_sgd": r["net"], "tax_sgd": r["tax"], "document_count": r["count"]}
        for code, r in output_by_code.items()
    ]
    input_rows = (
        [{"tax_code": "PURCHASES", "net_sgd": input_row["net"], "tax_sgd": input_row["tax"], "document_count": input_row["count"]}]
        if input_row["count"]
        else []
    )
    total_output = sum((r["tax_sgd"] for r in output_rows), Decimal("0.00"))
    total_input = sum((r["tax_sgd"] for r in input_rows), Decimal("0.00"))
    return {
        "output_rows": output_rows,
        "input_rows": input_rows,
        "total_output_tax_sgd": total_output,
        "total_input_tax_sgd": total_input,
        "net_gst_payable_sgd": total_output - total_input,
    }


# ---- Sales GP + Commission (2026-09-12, docs/open-business-decisions.md #32-#34) ----


def sales_gp_rows(
    db: Session, company_id: uuid.UUID, period_start: date, period_end: date
) -> list[dict]:
    """Every invoice issued in the date range with its GP -- see
    app/models/billing.py's docstring for what cost_sgd is and isn't
    (a point-in-time snapshot, null treated as zero cost)."""
    invoices = (
        db.query(Invoice)
        .filter(
            Invoice.company_id == company_id,
            Invoice.issued_at >= period_start,
            Invoice.issued_at <= period_end,
        )
        .order_by(Invoice.issued_at)
        .all()
    )
    rows = []
    for inv in invoices:
        cost = Decimal(inv.cost_sgd) if inv.cost_sgd is not None else Decimal("0.00")
        gp = Decimal(inv.amount_sgd) - cost
        gp_percent = (gp / Decimal(inv.amount_sgd) * 100) if Decimal(inv.amount_sgd) else Decimal("0.00")
        rows.append(
            {
                "invoice_id": inv.id,
                "invoice_number": inv.invoice_number,
                "issued_at": inv.issued_at,
                "customer_id": inv.customer_id,
                "revenue_sgd": Decimal(inv.amount_sgd),
                "cost_sgd": cost,
                "gp_sgd": gp,
                "gp_percent": gp_percent.quantize(Decimal("0.01")),
                "has_cost_basis": inv.cost_sgd is not None,
            }
        )
    return rows


def commission_rate_percent(db: Session, company_id: uuid.UUID) -> Decimal:
    """The admin-set commission rate (docs/open-business-decisions.md
    #34) -- zero until Dennis sets one, never invented."""
    settings = db.get(CommissionSettings, company_id)
    return Decimal(settings.rate_percent) if settings else Decimal("0.00")


def commission_rows(
    db: Session, company_id: uuid.UUID, period_start: date, period_end: date
) -> list[dict]:
    """Commission = rate% x GP, prorated by how much of the invoice a
    receipt actually settled, one row per (salesperson, month).

    Confirmed with Dennis, 2026-09-12: the formula is a flat percentage
    of gross profit, triggered by receipt allocation (not by invoicing)
    -- see PaymentAllocation (app/models/payments.py) for "Receipt
    Applied to Sales Invoice". The salesperson credited is the
    invoice's own Contract.sales_staff_id (already a first-class field,
    not invented here) -- an EXCESS_USAGE invoice's contract is used the
    same way. "Per month" groups by the receipt's own payment_date.
    An allocation's amount_sgd is against total_amount_sgd (includes
    GST), so it's first converted to its share of the invoice's *net*
    revenue before GP is applied, so GST never inflates commission."""
    rate = commission_rate_percent(db, company_id)
    allocations = (
        db.query(PaymentAllocation)
        .join(Invoice, PaymentAllocation.invoice_id == Invoice.id)
        .filter(
            PaymentAllocation.company_id == company_id,
        )
        .all()
    )
    totals: dict[tuple[str, uuid.UUID | None], Decimal] = {}
    for alloc in allocations:
        invoice = db.get(Invoice, alloc.invoice_id)
        payment = alloc.payment
        if payment is None or not (period_start <= payment.payment_date <= period_end):
            continue
        contract = db.get(Contract, invoice.contract_id) if invoice.contract_id else None
        sales_staff_id = contract.sales_staff_id if contract else None
        if Decimal(invoice.total_amount_sgd) == 0:
            continue
        net_share = Decimal(alloc.amount_sgd) * Decimal(invoice.amount_sgd) / Decimal(invoice.total_amount_sgd)
        gp_ratio = invoice.gp_percent / Decimal(100)
        commission = (net_share * gp_ratio * rate / Decimal(100)).quantize(Decimal("0.01"))
        month_key = payment.payment_date.strftime("%Y-%m")
        key = (month_key, sales_staff_id)
        totals[key] = totals.get(key, Decimal("0.00")) + commission

    return [
        {"month": month, "sales_staff_id": staff_id, "commission_sgd": amount}
        for (month, staff_id), amount in sorted(totals.items())
    ]
