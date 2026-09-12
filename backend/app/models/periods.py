"""
Accounting Periods, per-document-type operation locks, and Year-End
(Fiscal Year) Closing.

Period locks (2026-09-12, confirmed with Dennis):
  Each period carries a matrix of locks -- one per document-type ×
  operation combination.  Individual operations can be locked or
  unlocked independently, replacing the old binary OPEN/CLOSED toggle.
  "Close All" sets every lock; "Open All" clears every lock.  The
  `status` column stays on the period as a derived convenience
  indicator: OPEN when no lock is set, CLOSED when every valid lock is
  set.

  Document types:  SALES_INVOICE, RECEIPT_VOUCHER, PAYMENT_VOUCHER,
                   PURCHASE_BILL, JOURNAL_VOUCHER.
  Operations:      UPDATE, REVERSE, BANK, UNBANK, GL, UNGL.

  Not every operation applies to every doc type -- see
  VALID_DOC_OPERATIONS below.

Two pragmatic defaults (2026-09-11), still in effect:
  - Opt-in protection: a date with no period defined is unrestricted.
  - Fiscal year = whatever date range a period's rows say (plain date
    ranges, no hardcoded calendar).
"""
import enum
import uuid
from datetime import date, datetime

from sqlalchemy import (
    Boolean,
    Date,
    DateTime,
    Enum,
    ForeignKey,
    Integer,
    String,
    UniqueConstraint,
    func,
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base


# ── Enums ────────────────────────────────────────────────────────────


class PeriodStatus(str, enum.Enum):
    OPEN = "open"
    CLOSED = "closed"


class PeriodDocType(str, enum.Enum):
    """Accounting document types that participate in the period lock matrix."""
    SALES_INVOICE = "sales_invoice"
    RECEIPT_VOUCHER = "receipt_voucher"
    PAYMENT_VOUCHER = "payment_voucher"
    PURCHASE_BILL = "purchase_bill"
    JOURNAL_VOUCHER = "journal_voucher"


class PeriodOperation(str, enum.Enum):
    """Operations that can be individually locked per period per doc type."""
    UPDATE = "update"
    REVERSE = "reverse"
    BANK = "bank"
    UNBANK = "unbank"
    GL = "gl"
    UNGL = "ungl"


# Which operations are valid for which document type.
VALID_DOC_OPERATIONS: dict[PeriodDocType, list[PeriodOperation]] = {
    PeriodDocType.SALES_INVOICE: [
        PeriodOperation.UPDATE, PeriodOperation.REVERSE,
        PeriodOperation.GL, PeriodOperation.UNGL,
    ],
    PeriodDocType.RECEIPT_VOUCHER: [
        PeriodOperation.UPDATE, PeriodOperation.REVERSE,
        PeriodOperation.BANK, PeriodOperation.UNBANK,
        PeriodOperation.GL, PeriodOperation.UNGL,
    ],
    PeriodDocType.PAYMENT_VOUCHER: [
        PeriodOperation.UPDATE, PeriodOperation.REVERSE,
        PeriodOperation.BANK, PeriodOperation.UNBANK,
        PeriodOperation.GL, PeriodOperation.UNGL,
    ],
    PeriodDocType.PURCHASE_BILL: [
        PeriodOperation.UPDATE, PeriodOperation.REVERSE,
        PeriodOperation.GL, PeriodOperation.UNGL,
    ],
    PeriodDocType.JOURNAL_VOUCHER: [
        PeriodOperation.UPDATE, PeriodOperation.REVERSE,
        PeriodOperation.GL, PeriodOperation.UNGL,
    ],
}


# ── Models ───────────────────────────────────────────────────────────


class AccountingPeriod(Base):
    """One posting period (typically a calendar month) for a company.

    The `status` column is a derived convenience indicator kept in sync
    by the service layer:
      - OPEN  → every PeriodLock row for this period has is_locked=False
      - CLOSED → every PeriodLock row has is_locked=True
    Partial states (some locked, some not) show as OPEN in the DB but
    the frontend derives a "Partial" badge from the lock counts.
    """

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

    locks: Mapped[list["PeriodLock"]] = relationship(
        back_populates="period", cascade="all, delete-orphan"
    )


class PeriodLock(Base):
    """One cell of the period × document-type × operation lock matrix.

    Created automatically when a period is created (one row per valid
    combination from VALID_DOC_OPERATIONS). is_locked=False by default.
    """

    __tablename__ = "period_locks"
    __table_args__ = (
        UniqueConstraint("period_id", "doc_type", "operation", name="uq_period_lock"),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    period_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("accounting_periods.id"), nullable=False)
    doc_type: Mapped[PeriodDocType] = mapped_column(
        Enum(PeriodDocType, name="period_doc_type"), nullable=False
    )
    operation: Mapped[PeriodOperation] = mapped_column(
        Enum(PeriodOperation, name="period_operation"), nullable=False
    )
    is_locked: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    locked_by_user_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("users.id"), nullable=True)
    locked_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    period: Mapped["AccountingPeriod"] = relationship(back_populates="locks")


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
