"""
Bank Master File and the Currency Rate Table.

Both are setup/reference data only in this round -- no Receipt/Payment
Voucher or GL posting reads from a BankAccount or a CurrencyRate yet
(the whole app is single-currency, SGD, per CLAUDE.md's approved
architecture). Adding the master files now, without wiring them into
any calculation, is deliberate: it lets the data be set up ahead of
time without inventing multi-currency or bank-reconciliation business
rules nobody has confirmed.
"""
import uuid
from datetime import date, datetime
from decimal import Decimal

from sqlalchemy import Boolean, Date, DateTime, ForeignKey, Numeric, String, UniqueConstraint, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


class BankAccount(Base):
    """One of the company's own bank accounts -- the Bank Master File."""

    __tablename__ = "bank_accounts"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    company_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("companies.id"), nullable=False)
    bank_name: Mapped[str] = mapped_column(String(150), nullable=False)
    account_name: Mapped[str] = mapped_column(String(150), nullable=False)
    account_number: Mapped[str] = mapped_column(String(50), nullable=False)
    branch: Mapped[str | None] = mapped_column(String(150), nullable=True)
    swift_code: Mapped[str | None] = mapped_column(String(20), nullable=True)
    currency_code: Mapped[str] = mapped_column(String(3), nullable=False, default="SGD")
    # Optional link to the Chart of Accounts entry this account's cash
    # balance is booked under -- nothing posts to it automatically yet.
    gl_account_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("accounts.id"), nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class CurrencyRate(Base):
    """A currency's rate to the company's base currency (SGD) as at a
    given date -- a rate table only; nothing in the app converts an
    amount using it yet (see module docstring)."""

    __tablename__ = "currency_rates"
    __table_args__ = (
        UniqueConstraint("company_id", "currency_code", "effective_date", name="uq_currency_rate"),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    company_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("companies.id"), nullable=False)
    currency_code: Mapped[str] = mapped_column(String(3), nullable=False)
    rate_to_base: Mapped[Decimal] = mapped_column(Numeric(18, 6), nullable=False)
    effective_date: Mapped[date] = mapped_column(Date, nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
