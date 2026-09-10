"""
Accounts Receivable business logic.

Confirmed rules this implements:
- AR-001: payment allocation is **manual**. Finance decides which
  invoices a receipt settles; there is no automatic matching rule.
- AR-002: Finance may write off small amounts directly; above a
  threshold the owner approves. The threshold itself was never decided
  (open item 3.4), so it is a configurable field on the company and,
  while unset, EVERY write-off requires the owner -- the safe reading of
  an undecided rule, not an invented number.
- AR-003: a disputed invoice continues through normal collections and
  aging. Flagging a dispute records it for Finance; it holds nothing.
"""
import uuid
from datetime import date
from decimal import Decimal

from sqlalchemy.orm import Session

from app.models.billing import Invoice, InvoiceStatus
from app.models.core import Company, User, UserRole
from app.models.payments import Payment, PaymentAllocation


class ARRuleViolation(Exception):
    """A rule in this module was violated -- surfaced to the caller as a
    422 rather than a generic failure."""


# Aging buckets, by days past due.
AGING_BUCKETS = [
    ("current", None, 0),
    ("1_30", 1, 30),
    ("31_60", 31, 60),
    ("61_90", 61, 90),
    ("over_90", 91, None),
]


def recalculate_invoice_status(db: Session, invoice: Invoice) -> None:
    """Derive an invoice's paid state from what is allocated to it.

    Status is never set by hand (except a write-off), so it can't drift
    out of step with the payments actually applied.
    """
    if invoice.status == InvoiceStatus.WRITTEN_OFF:
        return

    allocated = (
        db.query(PaymentAllocation)
        .filter(PaymentAllocation.invoice_id == invoice.id)
        .all()
    )
    paid = sum((Decimal(a.amount_sgd) for a in allocated), start=Decimal("0.00"))
    invoice.amount_paid_sgd = paid

    total = Decimal(invoice.total_amount_sgd)
    if paid <= Decimal("0.00"):
        invoice.status = InvoiceStatus.OUTSTANDING
    elif paid >= total:
        invoice.status = InvoiceStatus.PAID
    else:
        invoice.status = InvoiceStatus.PARTIALLY_PAID


def allocate_payment(
    db: Session,
    payment: Payment,
    invoice: Invoice,
    amount: Decimal,
) -> PaymentAllocation:
    """Apply part (or all) of a payment to one invoice -- AR-001, always
    a manual decision by Finance."""
    amount = Decimal(amount)
    if amount <= Decimal("0.00"):
        raise ARRuleViolation("Allocation amount must be greater than zero.")
    if invoice.company_id != payment.company_id:
        raise ARRuleViolation("Invoice and payment belong to different companies.")
    if invoice.customer_id != payment.customer_id:
        raise ARRuleViolation(
            "That invoice belongs to a different customer than this payment."
        )
    if invoice.status == InvoiceStatus.WRITTEN_OFF:
        raise ARRuleViolation("That invoice has been written off.")
    if amount > payment.unallocated_sgd:
        raise ARRuleViolation(
            f"Only SGD {payment.unallocated_sgd} of this payment is still unallocated."
        )
    if amount > invoice.outstanding_sgd:
        raise ARRuleViolation(
            f"Invoice {invoice.invoice_number} only has SGD {invoice.outstanding_sgd} outstanding."
        )

    allocation = PaymentAllocation(
        company_id=payment.company_id,
        payment_id=payment.id,
        invoice_id=invoice.id,
        amount_sgd=amount,
    )
    db.add(allocation)
    db.flush()
    recalculate_invoice_status(db, invoice)
    return allocation


def can_write_off(db: Session, company_id: uuid.UUID, actor: User, amount: Decimal) -> bool:
    """AR-002. The owner can always write off. Anyone else can only do so
    below the configured threshold -- and while no threshold is set (it
    was never decided), nobody else can."""
    if actor.role == UserRole.OWNER:
        return True
    company = db.get(Company, company_id)
    threshold = company.write_off_approval_threshold_sgd if company else None
    if threshold is None:
        return False
    return Decimal(amount) <= Decimal(threshold)


def write_off_invoice(
    db: Session, invoice: Invoice, *, actor: User, reason: str
) -> Invoice:
    """AR-002: write off the outstanding balance as bad debt.

    The invoice is never deleted or altered -- it is marked written off
    and keeps its full history, per the rule that financial records are
    never destroyed.
    """
    if invoice.status == InvoiceStatus.WRITTEN_OFF:
        raise ARRuleViolation("That invoice has already been written off.")
    if invoice.status == InvoiceStatus.PAID:
        raise ARRuleViolation("That invoice is fully paid -- nothing to write off.")
    if not reason.strip():
        raise ARRuleViolation("A reason is required for every write-off (AR-002).")

    outstanding = invoice.outstanding_sgd
    if not can_write_off(db, invoice.company_id, actor, outstanding):
        company = db.get(Company, invoice.company_id)
        threshold = company.write_off_approval_threshold_sgd if company else None
        if threshold is None:
            raise ARRuleViolation(
                "No write-off approval threshold has been set, so every write-off needs "
                "the owner's approval (AR-002). Set a threshold in Company Setup, or ask "
                "the owner to action this."
            )
        raise ARRuleViolation(
            f"SGD {outstanding} is above the SGD {threshold} write-off threshold -- "
            "the owner must approve this (AR-002)."
        )

    invoice.status = InvoiceStatus.WRITTEN_OFF
    return invoice


def aging_bucket_for(due_date: date | None, as_at: date) -> str:
    """Which aging bucket an outstanding invoice falls into. An invoice
    with no due date (customer terms not agreed) is treated as current
    rather than overdue -- it cannot be late against a date that was
    never set."""
    if due_date is None or due_date >= as_at:
        return "current"
    days_overdue = (as_at - due_date).days
    for name, lower, upper in AGING_BUCKETS:
        if lower is None:
            continue
        if days_overdue >= lower and (upper is None or days_overdue <= upper):
            return name
    return "over_90"
