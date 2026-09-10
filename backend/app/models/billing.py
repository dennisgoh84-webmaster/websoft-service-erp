"""Billing models (single-line invoices for this build).

BILL-002: no approval required before issuing -- invoices are created
directly in "issued" status. A richer InvoiceLine breakdown is future
work (both invoice types raised today are single-line), not a
business-rule assumption.

GST: confirmed GST-registered, services standard-rated (see
app/models/tax.py). `amount_sgd` is the NET amount excluding GST -- it
stays the revenue figure, since GST collected is a liability owed to
IRAS, not income. `gst_amount_sgd` and `total_amount_sgd` carry the tax
and the amount the customer actually owes.
"""
import enum
import uuid
from datetime import date, datetime
from decimal import Decimal

from sqlalchemy import Boolean, Date, DateTime, Enum, ForeignKey, Numeric, String, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base


class InvoiceType(str, enum.Enum):
    CONTRACT_ANNUAL = "contract_annual"  # BILL-001
    EXCESS_USAGE = "excess_usage"  # SRV-008


class InvoiceStatus(str, enum.Enum):
    """Where an invoice sits in the AR cycle. Derived from payments
    allocated against it (see app/services/accounts_receivable.py) --
    never set by hand, except WRITTEN_OFF (AR-002)."""

    OUTSTANDING = "outstanding"
    PARTIALLY_PAID = "partially_paid"
    PAID = "paid"
    WRITTEN_OFF = "written_off"


class Invoice(Base):
    __tablename__ = "invoices"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    # Multi-company: the entity that issued this invoice.
    company_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("companies.id"), nullable=False)
    customer_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("customers.id"), nullable=False)
    contract_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("contracts.id"), nullable=True
    )
    excess_usage_record_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("excess_usage_records.id"), nullable=True
    )

    # Serially numbered per company per year -- a tax invoice must carry
    # an identifying number (see app/services/numbering.py).
    invoice_number: Mapped[str] = mapped_column(String(50), nullable=False, index=True)

    invoice_type: Mapped[InvoiceType] = mapped_column(Enum(InvoiceType, name="invoice_type"))
    description: Mapped[str] = mapped_column(String(500), nullable=False)

    # Net (excluding GST) -- the revenue figure.
    amount_sgd: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False)
    # The GST treatment as at the date this invoice was raised.
    tax_code: Mapped[str] = mapped_column(String(10), nullable=False, default="SR")
    gst_rate: Mapped[Decimal] = mapped_column(Numeric(5, 2), nullable=False, default=0)
    gst_amount_sgd: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False, default=0)
    # What the customer owes: net + GST.
    total_amount_sgd: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False, default=0)

    # AR: due date comes from the customer's payment terms (confirmed
    # 2026-09-10: terms vary per customer -- see Customer.payment_terms_days).
    due_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    status: Mapped[InvoiceStatus] = mapped_column(
        Enum(InvoiceStatus, name="invoice_status"), default=InvoiceStatus.OUTSTANDING
    )
    amount_paid_sgd: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False, default=0)
    # AR-003: a disputed invoice continues through normal collections and
    # aging -- this flags it for Finance, it does not hold anything.
    is_disputed: Mapped[bool] = mapped_column(Boolean, default=False)
    dispute_note: Mapped[str | None] = mapped_column(String(500), nullable=True)

    issued_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    customer: Mapped["Customer"] = relationship()  # noqa: F821

    @property
    def outstanding_sgd(self) -> Decimal:
        """What is still owed on this invoice (never negative)."""
        if self.status == InvoiceStatus.WRITTEN_OFF:
            return Decimal("0.00")
        return max(
            Decimal(self.total_amount_sgd) - Decimal(self.amount_paid_sgd), Decimal("0.00")
        )
