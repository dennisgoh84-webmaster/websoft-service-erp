"""
Accounts Receivable API -- customer payments, manual allocation (AR-001),
aging, statements, write-offs (AR-002) and dispute flagging (AR-003).

See app/services/accounts_receivable.py for the rules themselves.
"""
import uuid
from datetime import date
from decimal import Decimal

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session, selectinload

from app.core.database import get_db
from app.models.billing import Invoice, InvoiceStatus
from app.models.core import User
from app.models.customers import Customer
from app.models.groups import AccessLevel
from app.models.payments import Payment, PaymentMethod
from app.schemas.schemas import (
    AgingReport,
    AgingRow,
    AllocateRequest,
    CustomerStatement,
    InvoiceDisputeRequest,
    InvoiceWriteOffRequest,
    InvoiceOut,
    PaymentCreate,
    PaymentOut,
    StatementLine,
)
from app.services import accounts_receivable as ar_svc
from app.services import audit
from app.services.authority import require_module_access

router = APIRouter(prefix="/api/accounts-receivable", tags=["accounts-receivable"])
MODULE = "accounts_receivable"


def _invoice_or_404(db: Session, invoice_id: uuid.UUID, company_id: uuid.UUID) -> Invoice:
    invoice = db.get(Invoice, invoice_id)
    if not invoice or invoice.company_id != company_id:
        raise HTTPException(status_code=404, detail="Invoice not found")
    return invoice


def _payment_or_404(db: Session, payment_id: uuid.UUID, company_id: uuid.UUID) -> Payment:
    payment = (
        db.query(Payment)
        .options(selectinload(Payment.allocations))
        .filter(Payment.id == payment_id, Payment.company_id == company_id)
        .first()
    )
    if not payment:
        raise HTTPException(status_code=404, detail="Payment not found")
    return payment


def _invoice_numbers(db: Session, company_id: uuid.UUID) -> dict:
    return {
        i.id: i.invoice_number
        for i in db.query(Invoice).filter(Invoice.company_id == company_id).all()
    }


# ---- Payments -------------------------------------------------------


@router.post("/payments", response_model=PaymentOut)
def record_payment(
    payload: PaymentCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_module_access(MODULE, AccessLevel.EDIT)),
):
    """Record money received. Allocation is optional here -- AR-001 makes
    it a manual decision, so a receipt can sit unallocated on the
    customer's account until Finance decides what it settles."""
    customer = db.get(Customer, payload.customer_id)
    if not customer or customer.company_id != current_user.company_id:
        raise HTTPException(status_code=404, detail="Customer not found")

    try:
        method = PaymentMethod(payload.method)
    except ValueError:
        raise HTTPException(status_code=400, detail=f"Unknown payment method '{payload.method}'")

    payment = Payment(
        company_id=current_user.company_id,
        customer_id=payload.customer_id,
        payment_date=payload.payment_date,
        amount_sgd=Decimal(str(payload.amount_sgd)),
        method=method,
        reference=payload.reference,
        notes=payload.notes,
        recorded_by_user_id=current_user.id,
    )
    db.add(payment)
    db.flush()

    for entry in payload.allocations:
        invoice = _invoice_or_404(db, entry.invoice_id, current_user.company_id)
        try:
            ar_svc.allocate_payment(db, payment, invoice, Decimal(str(entry.amount_sgd)))
        except ar_svc.ARRuleViolation as e:
            raise HTTPException(status_code=422, detail=str(e))

    audit.record(
        db,
        entity_type="payment",
        entity_id=payment.id,
        action="recorded",
        actor_user_id=current_user.id,
        details=(
            f"SGD {payload.amount_sgd} from {customer.name} "
            f"({method.value}, ref={payload.reference or '-'})"
        ),
        new_value={
            "amount_sgd": str(payload.amount_sgd),
            "customer": customer.name,
            "allocations": len(payload.allocations),
        },
    )
    db.commit()
    db.refresh(payment)
    return PaymentOut.from_model(payment, _invoice_numbers(db, current_user.company_id))


@router.get("/payments", response_model=list[PaymentOut])
def list_payments(
    customer_id: uuid.UUID | None = None,
    unallocated_only: bool = False,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_module_access(MODULE, AccessLevel.VIEW)),
):
    query = (
        db.query(Payment)
        .options(selectinload(Payment.allocations))
        .filter(Payment.company_id == current_user.company_id)
    )
    if customer_id:
        query = query.filter(Payment.customer_id == customer_id)
    payments = query.order_by(Payment.payment_date.desc(), Payment.created_at.desc()).all()
    if unallocated_only:
        payments = [p for p in payments if p.unallocated_sgd > 0]
    numbers = _invoice_numbers(db, current_user.company_id)
    return [PaymentOut.from_model(p, numbers) for p in payments]


@router.post("/payments/{payment_id}/allocate", response_model=PaymentOut)
def allocate_payment(
    payment_id: uuid.UUID,
    payload: AllocateRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_module_access(MODULE, AccessLevel.EDIT)),
):
    """AR-001: Finance says which invoices this receipt settles."""
    payment = _payment_or_404(db, payment_id, current_user.company_id)

    applied = []
    for entry in payload.allocations:
        invoice = _invoice_or_404(db, entry.invoice_id, current_user.company_id)
        try:
            ar_svc.allocate_payment(db, payment, invoice, Decimal(str(entry.amount_sgd)))
        except ar_svc.ARRuleViolation as e:
            raise HTTPException(status_code=422, detail=str(e))
        applied.append(f"{invoice.invoice_number}={entry.amount_sgd}")

    audit.record(
        db,
        entity_type="payment",
        entity_id=payment.id,
        action="allocated",
        actor_user_id=current_user.id,
        details=", ".join(applied),
        new_value={"allocated_to": applied},
    )
    db.commit()
    db.refresh(payment)
    return PaymentOut.from_model(payment, _invoice_numbers(db, current_user.company_id))


# ---- Invoice actions ------------------------------------------------


@router.post("/invoices/{invoice_id}/write-off", response_model=InvoiceOut)
def write_off_invoice(
    invoice_id: uuid.UUID,
    payload: InvoiceWriteOffRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_module_access(MODULE, AccessLevel.EDIT)),
):
    """AR-002. The invoice is marked written off, never deleted."""
    invoice = _invoice_or_404(db, invoice_id, current_user.company_id)
    outstanding = invoice.outstanding_sgd
    try:
        ar_svc.write_off_invoice(db, invoice, actor=current_user, reason=payload.reason)
    except ar_svc.ARRuleViolation as e:
        raise HTTPException(status_code=422, detail=str(e))

    audit.record(
        db,
        entity_type="invoice",
        entity_id=invoice.id,
        action="written_off",
        actor_user_id=current_user.id,
        reason=payload.reason,
        details=f"{invoice.invoice_number}, SGD {outstanding} written off as bad debt",
        old_value={"status": "outstanding", "outstanding_sgd": str(outstanding)},
        new_value={"status": "written_off", "outstanding_sgd": "0.00"},
    )
    db.commit()
    db.refresh(invoice)
    return invoice


@router.post("/invoices/{invoice_id}/dispute", response_model=InvoiceOut)
def flag_dispute(
    invoice_id: uuid.UUID,
    payload: InvoiceDisputeRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_module_access(MODULE, AccessLevel.EDIT)),
):
    """AR-003: records that an invoice is disputed. It deliberately does
    NOT hold collections -- the invoice keeps aging normally."""
    invoice = _invoice_or_404(db, invoice_id, current_user.company_id)
    was = invoice.is_disputed
    invoice.is_disputed = payload.is_disputed
    invoice.dispute_note = payload.note

    audit.record(
        db,
        entity_type="invoice",
        entity_id=invoice.id,
        action="dispute_flagged" if payload.is_disputed else "dispute_cleared",
        actor_user_id=current_user.id,
        reason=payload.note,
        details=f"{invoice.invoice_number} (AR-003: collections continue regardless)",
        old_value={"is_disputed": was},
        new_value={"is_disputed": payload.is_disputed},
    )
    db.commit()
    db.refresh(invoice)
    return invoice


# ---- Reporting ------------------------------------------------------


@router.get("/aging", response_model=AgingReport)
def aging_report(
    as_at: date | None = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_module_access(MODULE, AccessLevel.VIEW)),
):
    """Outstanding balances bucketed by how far past due they are.

    AR-003: disputed invoices are included like any other -- they are
    flagged in the statement, not excluded from collections."""
    as_at = as_at or date.today()
    invoices = (
        db.query(Invoice)
        .filter(
            Invoice.company_id == current_user.company_id,
            Invoice.status != InvoiceStatus.PAID,
            Invoice.status != InvoiceStatus.WRITTEN_OFF,
        )
        .all()
    )
    customers = {
        c.id: c.name
        for c in db.query(Customer).filter(Customer.company_id == current_user.company_id).all()
    }

    buckets: dict[uuid.UUID, dict[str, Decimal]] = {}
    for invoice in invoices:
        outstanding = invoice.outstanding_sgd
        if outstanding <= 0:
            continue
        row = buckets.setdefault(
            invoice.customer_id,
            {"current": Decimal(0), "1_30": Decimal(0), "31_60": Decimal(0),
             "61_90": Decimal(0), "over_90": Decimal(0)},
        )
        row[ar_svc.aging_bucket_for(invoice.due_date, as_at)] += outstanding

    rows = [
        AgingRow(
            customer_id=customer_id,
            customer_name=customers.get(customer_id, "(unknown)"),
            current=float(b["current"]),
            days_1_30=float(b["1_30"]),
            days_31_60=float(b["31_60"]),
            days_61_90=float(b["61_90"]),
            over_90=float(b["over_90"]),
            total=float(sum(b.values())),
        )
        for customer_id, b in buckets.items()
    ]
    rows.sort(key=lambda r: r.total, reverse=True)

    return AgingReport(
        as_at=as_at,
        rows=rows,
        current=sum(r.current for r in rows),
        days_1_30=sum(r.days_1_30 for r in rows),
        days_31_60=sum(r.days_31_60 for r in rows),
        days_61_90=sum(r.days_61_90 for r in rows),
        over_90=sum(r.over_90 for r in rows),
        total=sum(r.total for r in rows),
    )


@router.get("/statement/{customer_id}", response_model=CustomerStatement)
def customer_statement(
    customer_id: uuid.UUID,
    as_at: date | None = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_module_access(MODULE, AccessLevel.VIEW)),
):
    """Everything this customer currently owes, plus any receipt money
    still sitting unallocated on their account."""
    as_at = as_at or date.today()
    customer = db.get(Customer, customer_id)
    if not customer or customer.company_id != current_user.company_id:
        raise HTTPException(status_code=404, detail="Customer not found")

    invoices = (
        db.query(Invoice)
        .filter(
            Invoice.company_id == current_user.company_id,
            Invoice.customer_id == customer_id,
            Invoice.status != InvoiceStatus.PAID,
        )
        .order_by(Invoice.issued_at)
        .all()
    )

    lines = [
        StatementLine(
            invoice_id=i.id,
            invoice_number=i.invoice_number,
            description=i.description,
            issued_on=i.issued_at.date(),
            due_date=i.due_date,
            total_amount_sgd=float(i.total_amount_sgd),
            amount_paid_sgd=float(i.amount_paid_sgd),
            outstanding_sgd=float(i.outstanding_sgd),
            status=i.status.value,
            is_disputed=i.is_disputed,
            days_overdue=(
                max((as_at - i.due_date).days, 0) if i.due_date else 0
            ),
        )
        for i in invoices
    ]

    payments = (
        db.query(Payment)
        .options(selectinload(Payment.allocations))
        .filter(Payment.company_id == current_user.company_id, Payment.customer_id == customer_id)
        .all()
    )
    unallocated = sum((p.unallocated_sgd for p in payments), start=Decimal("0.00"))

    return CustomerStatement(
        customer_id=customer.id,
        customer_name=customer.name,
        as_at=as_at,
        payment_terms_days=customer.payment_terms_days,
        lines=lines,
        total_outstanding_sgd=float(sum(Decimal(str(l.outstanding_sgd)) for l in lines)),
        unallocated_credit_sgd=float(unallocated),
    )
