"""Sales Quotation.

Confirmed 2026-09-10: a standalone document that, on acceptance,
attempts to auto-create a draft Service Contract from it (the confirmed
SRV-001/002 rules on that contract are unchanged and unbypassed). See
app/services/quotations.py for the conversion logic and its one
still-open point: how a quotation's mixed-unit line items (Hours,
Monthly, Yearly, Units, SET...) map onto a single Contract's
contracted_hours has not been confirmed as a business rule -- only
lines whose unit_of_measure is "Hours" count toward it today, so a
quotation with no hourly lines (e.g. pure subscription items) cannot
auto-convert, because the contract's 10-hour minimum (SRV-002/012) has
no override mechanism. Logged in docs/open-business-decisions.md;
revisit once the real conversion rule is confirmed.
"""
import enum
import uuid
from datetime import date, datetime
from decimal import Decimal

from sqlalchemy import Date, DateTime, Enum, ForeignKey, Numeric, String, Text, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base


class QuotationStatus(str, enum.Enum):
    draft = "draft"
    sent = "sent"
    accepted = "accepted"
    rejected = "rejected"
    expired = "expired"


class Quotation(Base):
    __tablename__ = "quotations"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    company_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("companies.id"), nullable=False)
    quotation_number: Mapped[str] = mapped_column(String(50), nullable=False)
    customer_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("customers.id"), nullable=False)
    quotation_date: Mapped[date] = mapped_column(Date, nullable=False)
    valid_until: Mapped[date | None] = mapped_column(Date, nullable=True)
    status: Mapped[QuotationStatus] = mapped_column(
        Enum(QuotationStatus, name="quotation_status"), nullable=False, default=QuotationStatus.draft
    )
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)

    # Net of GST -- see app/services/quotations.py's recompute_totals,
    # same single-rate-per-document pattern as Invoice.
    amount_sgd: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False, default=0)
    tax_code: Mapped[str] = mapped_column(String(10), nullable=False, default="SR")
    gst_rate: Mapped[Decimal] = mapped_column(Numeric(5, 2), nullable=False, default=0)
    gst_amount_sgd: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False, default=0)
    total_amount_sgd: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False, default=0)

    # Set only if Accept auto-converted this quotation -- see module
    # docstring for when it does/doesn't.
    converted_contract_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("contracts.id"), nullable=True
    )
    created_by_user_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("users.id"), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    lines: Mapped[list["QuotationLine"]] = relationship(
        back_populates="quotation", order_by="QuotationLine.id", cascade="all, delete-orphan"
    )


class QuotationLine(Base):
    __tablename__ = "quotation_lines"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    quotation_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("quotations.id"), nullable=False)
    # Optional: a line can still be free text if it doesn't match a
    # catalog item, but picking one pre-fills description/price/UoM.
    product_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("products.id"), nullable=True)
    # Stored on the line so the quotation text stays exactly as sent
    # even if the catalog item is later renamed or deactivated.
    description: Mapped[str] = mapped_column(String(255), nullable=False)
    unit_of_measure: Mapped[str | None] = mapped_column(String(50), nullable=True)
    quantity: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False, default=1)
    unit_price_sgd: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False, default=0)
    line_total_sgd: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False, default=0)

    quotation: Mapped["Quotation"] = relationship(back_populates="lines")
