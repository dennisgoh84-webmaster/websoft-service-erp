"""
Accounting Period locking (granular, per-doc-type per-operation) and
the Year-End Closing action.

See app/models/periods.py for the lock matrix, the VALID_DOC_OPERATIONS
mapping, and the two pragmatic defaults (opt-in protection; fiscal year
is whatever the period rows say).

Updated 2026-09-12: replaced binary OPEN/CLOSED enforcement with a
per-document-type, per-operation lock matrix.  ``require_open_period``
is kept as a backward-compatible wrapper (checks UPDATE for a given
doc type); new code should call ``require_period_allows`` directly.
"""
import uuid
from datetime import date, datetime, timedelta, timezone
from decimal import Decimal

from sqlalchemy.orm import Session

from app.models.accounting import Account, AccountType, JournalEntry, VoucherType
from app.models.periods import (
    AccountingPeriod,
    FiscalYearClosure,
    PeriodDocType,
    PeriodLock,
    PeriodOperation,
    PeriodStatus,
    VALID_DOC_OPERATIONS,
)


# ── Exceptions ───────────────────────────────────────────────────────


class PeriodClosedError(Exception):
    """A transaction date falls inside a period that has this operation locked."""


class PeriodLockedError(PeriodClosedError):
    """More descriptive subclass; same catch semantics."""


class YearEndClosingError(Exception):
    """A Year-End Closing precondition wasn't met."""


# ── Helpers: VoucherType → PeriodDocType ─────────────────────────────


_VOUCHER_TO_DOC: dict[VoucherType, PeriodDocType] = {
    VoucherType.JOURNAL: PeriodDocType.JOURNAL_VOUCHER,
    VoucherType.RECEIPT: PeriodDocType.RECEIPT_VOUCHER,
    VoucherType.PAYMENT: PeriodDocType.PAYMENT_VOUCHER,
    VoucherType.SALES_INVOICE: PeriodDocType.SALES_INVOICE,
    VoucherType.PURCHASE_INVOICE: PeriodDocType.PURCHASE_BILL,
}


def voucher_type_to_doc_type(vt: VoucherType) -> PeriodDocType:
    """Map a GL VoucherType to the corresponding PeriodDocType."""
    return _VOUCHER_TO_DOC[vt]


# ── Period lookup ────────────────────────────────────────────────────


def get_period_for_date(db: Session, company_id: uuid.UUID, on: date) -> AccountingPeriod | None:
    return (
        db.query(AccountingPeriod)
        .filter(
            AccountingPeriod.company_id == company_id,
            AccountingPeriod.period_start <= on,
            AccountingPeriod.period_end >= on,
        )
        .first()
    )


# ── Granular lock checks ────────────────────────────────────────────


def require_period_allows(
    db: Session,
    company_id: uuid.UUID,
    on: date,
    doc_type: PeriodDocType,
    operation: PeriodOperation,
) -> None:
    """Raise ``PeriodLockedError`` if ``operation`` is locked for
    ``doc_type`` in the period covering ``on``.  A date with no period
    defined is unrestricted (opt-in protection)."""
    period = get_period_for_date(db, company_id, on)
    if period is None:
        return
    lock = (
        db.query(PeriodLock)
        .filter(
            PeriodLock.period_id == period.id,
            PeriodLock.doc_type == doc_type,
            PeriodLock.operation == operation,
            PeriodLock.is_locked.is_(True),
        )
        .first()
    )
    if lock:
        op_label = operation.value.upper()
        doc_label = doc_type.value.replace("_", " ").title()
        raise PeriodLockedError(
            f'{op_label} is locked for {doc_label} in period "{period.name}" '
            f"({period.period_start.isoformat()} to {period.period_end.isoformat()}). "
            f"Unlock it under Accounting Periods, or use a date in an unlocked period."
        )


def require_open_period(db: Session, company_id: uuid.UUID, on: date) -> None:
    """Backward-compatible wrapper: checks the old OPEN/CLOSED status.

    New code should call ``require_period_allows`` with the specific
    doc_type and operation.  This wrapper exists so callers that haven't
    been migrated yet still block on a fully-closed period."""
    period = get_period_for_date(db, company_id, on)
    if period is not None and period.status == PeriodStatus.CLOSED:
        raise PeriodClosedError(
            f'The accounting period "{period.name}" ({period.period_start.isoformat()} to '
            f"{period.period_end.isoformat()}) is closed for posting. Ask an owner to reopen "
            "it under Accounting Periods, or use a date in an open period."
        )


# ── Lock seed (called when a period is created) ─────────────────────


def seed_locks_for_period(db: Session, period: AccountingPeriod, *, locked: bool = False) -> None:
    """Create one PeriodLock row for every valid doc-type × operation."""
    for doc_type, operations in VALID_DOC_OPERATIONS.items():
        for op in operations:
            db.add(PeriodLock(
                period_id=period.id,
                doc_type=doc_type,
                operation=op,
                is_locked=locked,
            ))
    db.flush()


# ── Lock / unlock ────────────────────────────────────────────────────


def _sync_period_status(db: Session, period: AccountingPeriod, *, actor_user_id: uuid.UUID | None = None) -> None:
    """Derive the period's status from its lock rows."""
    locks = db.query(PeriodLock).filter(PeriodLock.period_id == period.id).all()
    all_locked = all(lk.is_locked for lk in locks)
    if all_locked and locks:
        period.status = PeriodStatus.CLOSED
        period.closed_by_user_id = actor_user_id
        period.closed_at = datetime.now(timezone.utc) if actor_user_id else period.closed_at
    else:
        period.status = PeriodStatus.OPEN
        if not any(lk.is_locked for lk in locks):
            # Fully open → clear the "last closed by" metadata
            period.closed_by_user_id = None
            period.closed_at = None


def set_all_locks(
    db: Session,
    period: AccountingPeriod,
    *,
    locked: bool,
    actor_user_id: uuid.UUID,
) -> None:
    """Lock or unlock every operation for every doc type in one action."""
    now = datetime.now(timezone.utc)
    locks = db.query(PeriodLock).filter(PeriodLock.period_id == period.id).all()
    for lk in locks:
        lk.is_locked = locked
        lk.locked_by_user_id = actor_user_id if locked else None
        lk.locked_at = now if locked else None
    _sync_period_status(db, period, actor_user_id=actor_user_id)


def toggle_lock(
    db: Session,
    period: AccountingPeriod,
    doc_type: PeriodDocType,
    operation: PeriodOperation,
    *,
    locked: bool,
    actor_user_id: uuid.UUID,
) -> PeriodLock:
    """Lock or unlock a single doc-type × operation cell."""
    if operation not in VALID_DOC_OPERATIONS.get(doc_type, []):
        raise ValueError(f"{operation.value} is not a valid operation for {doc_type.value}")
    lk = (
        db.query(PeriodLock)
        .filter(
            PeriodLock.period_id == period.id,
            PeriodLock.doc_type == doc_type,
            PeriodLock.operation == operation,
        )
        .first()
    )
    if lk is None:
        raise ValueError(f"No lock row found for {doc_type.value}/{operation.value}")
    now = datetime.now(timezone.utc)
    lk.is_locked = locked
    lk.locked_by_user_id = actor_user_id if locked else None
    lk.locked_at = now if locked else None
    _sync_period_status(db, period, actor_user_id=actor_user_id)
    return lk


# ── Legacy wrappers (still used by year-end closing) ─────────────────


def close_period(db: Session, period: AccountingPeriod, *, actor_user_id: uuid.UUID) -> None:
    """Lock every operation (Close All)."""
    set_all_locks(db, period, locked=True, actor_user_id=actor_user_id)


def reopen_period(db: Session, period: AccountingPeriod) -> None:
    """Unlock every operation (Open All)."""
    now = datetime.now(timezone.utc)
    locks = db.query(PeriodLock).filter(PeriodLock.period_id == period.id).all()
    for lk in locks:
        lk.is_locked = False
        lk.locked_by_user_id = None
        lk.locked_at = None
    period.status = PeriodStatus.OPEN
    period.closed_by_user_id = None
    period.closed_at = None


# ── Year-End Closing ─────────────────────────────────────────────────


def close_fiscal_year(
    db: Session,
    *,
    company_id: uuid.UUID,
    fiscal_year: int,
    retained_earnings_account_id: uuid.UUID,
    actor_user_id: uuid.UUID,
) -> JournalEntry:
    """Zero every Revenue/Expense account's movement for `fiscal_year`
    into `retained_earnings_account_id` with one balanced closing
    journal entry, then record the closure. Every period tagged with
    this fiscal year must already be closed -- this only moves balances
    that are no longer expected to change.

    Reversible: the closing entry is an ordinary posted JournalEntry, so
    undoing a mistaken close is done the same way any posted voucher is
    corrected -- app/services/ledger.py's reverse_entry -- rather than a
    separate "unclose" mechanism."""
    from app.services import ledger as ledger_svc

    periods = (
        db.query(AccountingPeriod)
        .filter(AccountingPeriod.company_id == company_id, AccountingPeriod.fiscal_year == fiscal_year)
        .all()
    )
    if not periods:
        raise YearEndClosingError(f"No accounting periods are defined for fiscal year {fiscal_year}.")
    if any(p.status != PeriodStatus.CLOSED for p in periods):
        raise YearEndClosingError(
            f"Every period in fiscal year {fiscal_year} must be closed (all operations locked) "
            "before year-end closing."
        )
    already = (
        db.query(FiscalYearClosure)
        .filter(FiscalYearClosure.company_id == company_id, FiscalYearClosure.fiscal_year == fiscal_year)
        .first()
    )
    if already:
        raise YearEndClosingError(f"Fiscal year {fiscal_year} has already been closed.")

    re_account = db.get(Account, retained_earnings_account_id)
    if re_account is None or re_account.company_id != company_id:
        raise YearEndClosingError("Unknown Retained Earnings account.")
    if re_account.account_type != AccountType.EQUITY:
        raise YearEndClosingError(f"{re_account.code} {re_account.name} is not an Equity account.")

    fy_start = min(p.period_start for p in periods)
    fy_end = max(p.period_end for p in periods)
    day_before = fy_start - timedelta(days=1)

    balances_end = {r["account_id"]: r["balance_sgd"] for r in ledger_svc.account_balances(db, company_id, fy_end)}
    balances_before = {
        r["account_id"]: r["balance_sgd"] for r in ledger_svc.account_balances(db, company_id, day_before)
    }
    accounts_by_id = {a.id: a for a in db.query(Account).filter(Account.company_id == company_id).all()}

    lines: list[dict] = []
    total_fy_balance = Decimal("0.00")
    for account_id, end_balance in balances_end.items():
        account = accounts_by_id.get(account_id)
        if account is None or account.account_type not in (AccountType.REVENUE, AccountType.EXPENSE):
            continue
        fy_balance = end_balance - balances_before.get(account_id, Decimal("0.00"))
        if fy_balance == 0:
            continue
        total_fy_balance += fy_balance
        if fy_balance > 0:
            lines.append(
                {
                    "account_id": account_id,
                    "debit_sgd": Decimal("0.00"),
                    "credit_sgd": fy_balance,
                    "description": f"FY{fiscal_year} close: {account.code} {account.name}",
                }
            )
        else:
            lines.append(
                {
                    "account_id": account_id,
                    "debit_sgd": -fy_balance,
                    "credit_sgd": Decimal("0.00"),
                    "description": f"FY{fiscal_year} close: {account.code} {account.name}",
                }
            )

    if not lines:
        raise YearEndClosingError(
            f"No Revenue or Expense activity found in fiscal year {fiscal_year} -- nothing to close."
        )

    if total_fy_balance > 0:
        lines.append(
            {
                "account_id": retained_earnings_account_id,
                "debit_sgd": total_fy_balance,
                "credit_sgd": Decimal("0.00"),
                "description": f"FY{fiscal_year} net loss to retained earnings",
            }
        )
    else:
        lines.append(
            {
                "account_id": retained_earnings_account_id,
                "debit_sgd": Decimal("0.00"),
                "credit_sgd": -total_fy_balance,
                "description": f"FY{fiscal_year} net profit to retained earnings",
            }
        )

    entry = ledger_svc.create_journal_entry(
        db,
        company_id=company_id,
        entry_date=fy_end,
        narration=f"Year-end closing FY{fiscal_year}: Revenue/Expense closed to {re_account.code} {re_account.name}",
        lines=lines,
        voucher_type=VoucherType.JOURNAL,
        created_by_user_id=actor_user_id,
        source_type="fiscal_year_closure",
    )
    ledger_svc.post_entry(db, entry, actor_user_id=actor_user_id, bypass_period_check=True)
    db.flush()

    closure = FiscalYearClosure(
        company_id=company_id,
        fiscal_year=fiscal_year,
        retained_earnings_account_id=retained_earnings_account_id,
        closing_journal_entry_id=entry.id,
        closed_by_user_id=actor_user_id,
    )
    db.add(closure)
    db.flush()
    return entry
