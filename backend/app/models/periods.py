"""
Accounting Periods and Year-End (Fiscal Year) Closing.

Confirmed 2026-09-11 (in response to an explicit scope question, since
"what does closing a year actually do" is exactly the kind of thing
CLAUDE.md says never to assume): this round covers period open/close
locking (no posting into a closed period), a read-only GST return
report, and a full year-end close that posts one closing journal moving
Revenue/Expense balances to an admin-chosen Equity account.

Two pragmatic defaults, not separately confirmed, logged here and in
docs/open-business-decisions.md:
  - A period is opt-in protection: if no AccountingPeriod row covers a
    given date at all, posting is unrestricted for that date (so
    turning this feature on cannot retroactively break existing data
    or dates nobody has defined a period for yet). Only a period
    explicitly marked CLOSED blocks posting.
  - Fiscal year = calendar year (Jan-Dec) unless a company defines its
    periods otherwise -- periods are plain date ranges, not derived
    from a hardcoded calendar, so this can differ per period row if a
    non-calendar fiscal year is decided later.
"""
import enum
import uuid
from datetime import date, datetime

from sqlalchemy import Date, DateTime, Enum, ForeignKey, Integer, String, UniqueConstraint, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base


class PeriodStatus(str, enum.Enum):
    OPEN = "open"
    CLOSED = "closed"


class AccountingPeriod(Base):
    """One posting period (typically a calendar month) for a company.
    Closing a period blocks new JV postings, invoices, bills, receipts
    and payments dated inside it -- see app/services/periods.py."""

    __tablename__ = "accounting_periods"
    __table_args__ = (
        UniqueConstraint("company_id", "period_start", name="uq_accounting_period_start"),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    company_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("companies.id"), nullable=False)
    fiscal_year: Mapped[int] = mapped_column(Integer, nullable=False)
    name: Mapped[str] = mapped_column(String(50), nullable=False)  # e.g. "2026-09" / "Sep 2026"
    period_start: Mapped[date] = mapped_column(Date, nullable=False)
    period_end: Mapped[date] = mapped_column(Date, nullable=False)
    status: Mapped[PeriodStatus] = mapped_column(
        Enum(PeriodStatus, name="period_status"), default=PeriodStatus.OPEN
    )
    closed_by_user_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("users.id"), nullable=True)
    closed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class FiscalYearClosure(Base):
    """Record of a Year-End Close: every period in `fiscal_year` was
    already closed, and `closing_journal_entry_id` is the one voucher
    that zeroed Revenue/Expense into `retained_earnings_account_id`.
    Never deleted -- if the close needs to be undone, the closing
    journal entry itself is reversed (app/services/ledger.py
    reverse_entry), which stays visible in the ledger and Event Logs
    rather than erasing this record."""

    __tablename__ = "fiscal_year_closures"
    __table_args__ = (
        UniqueConstraint("company_id", "fiscal_year", name="uq_fiscal_year_closure"),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    company_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("companies.id"), nullable=False)
    fiscal_year: Mapped[int] = mapped_column(Integer, nullable=False)
    retained_earnings_account_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("accounts.id"), nullable=False
    )
    closing_journal_entry_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("journal_entries.id"), nullable=False
    )
    closed_by_user_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("users.id"), nullable=True)
    closed_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    closing_journal_entry = relationship("JournalEntry")
