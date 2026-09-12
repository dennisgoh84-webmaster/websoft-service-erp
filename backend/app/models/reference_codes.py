"""Reference Monitor -- sub-codes of one Chart of Accounts row.

Requested 2026-09-12: a single GL code (e.g. 45001 "Sales of Software
Revenue") needs to be broken down into several named sub-codes for
document selection -- e.g. SLS-WEBSOFT-IMPLEMENTATION, SLS-WEBSOFT-
SERVICE, SLS-WEBSOFT-STOCK, SLS-WEBSOFT-CUSTOMIZATIONS, all posting to
the same 45001 account -- so a Product can carry a default one and a
document line can capture (or override) which sub-code it was for.

Deliberately narrow first slice: a ReferenceCode is a plain child of one
Account (Chart of Accounts) row, presettable on a Product
(`Product.default_reference_code_id`) and captured on a Quotation Line
(`QuotationLine.reference_code_id`, auto-filled from the chosen
product's default, overridable) -- the only document type in this
system with real per-line item selection today. No document type here
auto-posts to the General Ledger yet (Journal Vouchers are entered
manually only, see app/routers/ledger.py) -- so the "eventually post to
Chart of Accounts transactions" half of the request is recorded as
future scope (docs/open-business-decisions.md #25... see planned-work.md)
rather than built now: there is nothing yet for a captured reference
code to drive.
"""
import uuid
from datetime import datetime

from sqlalchemy import Boolean, DateTime, ForeignKey, String, UniqueConstraint, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base


class ReferenceCode(Base):
    __tablename__ = "reference_codes"
    __table_args__ = (UniqueConstraint("company_id", "code", name="uq_reference_code"),)

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    company_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("companies.id"), nullable=False)
    # The one Chart of Accounts row this sub-code posts to/breaks down.
    account_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("accounts.id"), nullable=False)
    code: Mapped[str] = mapped_column(String(50), nullable=False)
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    account: Mapped["Account"] = relationship()  # noqa: F821
