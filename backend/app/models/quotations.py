"""Sales Quotation.

Confirmed 2026-09-10: a standalone document that, on acceptance,
attempts to auto-create Contract(s) from it. There are two kinds of
Contract (app/models/contracts.py's ContractKind): SERVICE_SUPPORT
(hours-based, SRV-002/012's 10-hour minimum applies) and ANNUAL
(term-only, e.g. an annual software warranty/maintenance contract --
no hours at all). A quotation's lines are split by unit of measure:
lines whose unit is "Hours"/"Hour" become one SERVICE_SUPPORT contract
(summed hours + their value); every other line becomes one ANNUAL
contract (summed value, standard 12-month term). A quotation can
convert to either, both, or neither, depending on what lines it has --
see app/services/quotations.py's accept_quotation.
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
    customer_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("company_individuals.id"), nullable=False)
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

    # Set only if Accept auto-converted this quotation. Confirmed
    # 2026-09-10: a quotation mixing hourly and non-hourly lines
    # converts to TWO separate contracts, never one blending both --
    # converted_contract_id is the SERVICE_SUPPORT contract (from
    # "Hours" lines), converted_annual_contract_id is the ANNUAL
    # contract (from every other line, by value). Either or both may be
    # null depending on what lines the quotation actually had.
    converted_contract_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("contracts.id"), nullable=True
    )
    converted_annual_contract_id: Mapped[uuid.UUID | None] = mapped_column(
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
    # Reference Monitor (2026-09-12): which GL sub-code (see
    # app/models/reference_codes.py) this line was for -- auto-filled
    # from the chosen product's default_reference_code_id, but always
    # overridable per line. Optional: a free-text line has no product to
    # default from, and not every line needs one classified.
    reference_code_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("reference_codes.id"), nullable=True
    )
    # Costing (2026-09-12): the product cost behind this line, so a
    # later GP report can compare it against unit_price_sgd/line_total_sgd.
    # Auto-filled from the chosen product's Product.cost_sgd, but always
    # an open, overridable field -- a non-product (free-text) line has no
    # product to default from, so this is the only place its cost comes
    # from. See app/services/quotations.py for the auto-fill.
    cost_sgd: Mapped[Decimal | None] = mapped_column(Numeric(12, 2), nullable=True)

    quotation: Mapped["Quotation"] = relationship(back_populates="lines")
