"""
GST / tax codes.

Confirmed with Dennis (2026-09-10): Webmaster Consultancy is
GST-registered and its services are standard-rated. Rather than hard-code
a rate, the rate lives in a tax code table so a rate change (Singapore
has moved twice in recent years) is a data change, and so zero-rated or
exempt supplies can be added later without a re-model.

Every invoice stores the rate it was raised at (see Invoice.gst_rate),
not a pointer to the current rate -- a historical invoice must keep
showing the GST that was actually charged.
"""
import uuid
from decimal import Decimal

from sqlalchemy import Boolean, ForeignKey, Numeric, String, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base

# The tax code applied to Webmaster's service billing today. Standard-
# rated supplies -- confirmed by Dennis, 2026-09-10.
DEFAULT_TAX_CODE = "SR"


class TaxCode(Base):
    """A GST treatment: its code, description and rate."""

    __tablename__ = "tax_codes"
    __table_args__ = (UniqueConstraint("company_id", "code", name="uq_tax_code"),)

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    company_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("companies.id"), nullable=False)
    code: Mapped[str] = mapped_column(String(10), nullable=False)
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    rate_percent: Mapped[Decimal] = mapped_column(Numeric(5, 2), nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
