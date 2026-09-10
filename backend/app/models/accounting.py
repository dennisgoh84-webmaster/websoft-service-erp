"""
Chart of accounts.

Confirmed with Dennis (2026-09-10): start from a conventional Singapore
SME chart and adjust it, rather than importing Odoo's. The seeded
accounts in scripts/seed_demo.py are therefore a STARTING POINT, not a
decided chart -- every account can be renamed, added or deactivated from
the Chart of Accounts screen.

This stage establishes the account structure only. Posting AR/AP/billing
transactions into a general ledger against these accounts comes with the
Finance / Accounting module; nothing posts yet, so no assumption is made
about which account each transaction hits.
"""
import enum
import uuid
from datetime import datetime

from sqlalchemy import Boolean, DateTime, Enum, ForeignKey, String, Text, UniqueConstraint, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


class AccountType(str, enum.Enum):
    """The five standard account classes. An account's type decides which
    financial statement it belongs to and its normal balance."""

    ASSET = "asset"
    LIABILITY = "liability"
    EQUITY = "equity"
    REVENUE = "revenue"
    EXPENSE = "expense"


class Account(Base):
    """One line of the chart of accounts."""

    __tablename__ = "accounts"
    __table_args__ = (UniqueConstraint("company_id", "code", name="uq_account_code"),)

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    # Chart of accounts is per company, like everything else.
    company_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("companies.id"), nullable=False)
    code: Mapped[str] = mapped_column(String(20), nullable=False)
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    account_type: Mapped[AccountType] = mapped_column(
        Enum(AccountType, name="account_type"), nullable=False
    )
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    # Retired rather than deleted -- an account that has been posted to
    # must remain for the history to stay readable.
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
