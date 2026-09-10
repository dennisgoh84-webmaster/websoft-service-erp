"""Billing models (minimal slice: single-line invoices for this build).

BILL-002: no approval required before issuing -- invoices are created
directly in "issued" status. A richer InvoiceLine breakdown and
approval workflow are future work, not a business-rule assumption.
"""
import enum
import uuid
from datetime import datetime

from sqlalchemy import DateTime, Enum, ForeignKey, Numeric, String, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base


class InvoiceType(str, enum.Enum):
    CONTRACT_ANNUAL = "contract_annual"  # BILL-001
    EXCESS_USAGE = "excess_usage"  # SRV-008


class Invoice(Base):
    __tablename__ = "invoices"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    customer_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("customers.id"), nullable=False)
    contract_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("contracts.id"), nullable=True
    )
    excess_usage_record_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("excess_usage_records.id"), nullable=True
    )

    invoice_type: Mapped[InvoiceType] = mapped_column(Enum(InvoiceType, name="invoice_type"))
    description: Mapped[str] = mapped_column(String(500), nullable=False)
    amount_sgd: Mapped[float] = mapped_column(Numeric(12, 2), nullable=False)

    issued_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    customer: Mapped["Customer"] = relationship()  # noqa: F821
