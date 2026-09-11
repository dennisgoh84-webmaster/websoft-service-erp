"""
Accounting Period locking and the Year-End Closing action.

See app/models/periods.py for the two pragmatic, explicitly-flagged
defaults this implements (periods are opt-in protection; fiscal year is
whatever date range a period's rows say, not a hardcoded calendar).
"""
import uuid
from datetime import date, timedelta
from decimal import Decimal

from sqlalchemy.orm import Session

from app.models.accounting import Account, AccountType, JournalEntry, VoucherType
from app.models.periods import AccountingPeriod, FiscalYearClosure, PeriodStatus


class PeriodClosedError(Exception):
    """A transaction date falls inside a period explicitly closed for posting."""


class YearEndClosingError(Exception):
    """A Year-End Closing precondition wasn't met."""


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


def require_open_period(db: Session, company_id: uuid.UUID, on: date) -> None:
    """Raise PeriodClosedError if `on` falls inside a CLOSED period. A
    date with no period defined at all is unrestricted -- see the
    "opt-in protection" default in app/models/periods.py."""
    period = get_period_for_date(db, company_id, on)
    if period is not None and period.status == PeriodStatus.CLOSED:
        raise PeriodClosedError(
            f'The accounting period "{period.name}" ({period.period_start.isoformat()} to '
            f"{period.period_end.isoformat()}) is closed for posting. Ask an owner to reopen "
            "it under Accounting Periods, or use a date in an open period."
        )


def close_period(db: Session, period: AccountingPeriod, *, actor_user_id: uuid.UUID) -> None:
    from datetime import datetime, timezone

    period.status = PeriodStatus.CLOSED
    period.closed_by_user_id = actor_user_id
    period.closed_at = datetime.now(timezone.utc)


def reopen_period(db: Session, period: AccountingPeriod) -> None:
    period.status = PeriodStatus.OPEN
    period.closed_by_user_id = None
    period.closed_at = None


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
            f"Every period in fiscal year {fiscal_year} must be closed before year-end closing."
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

    # Offsetting line: see app/services/periods.py's close_fiscal_year
    # docstring math -- a positive total_fy_balance (net debit across
    # P&L, i.e. a loss) needs RE debited; a negative total (net credit,
    # a profit) needs RE credited.
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
    # Every period in this fiscal year is closed by definition here, so
    # the normal period-lock check (which would otherwise refuse to post
    # a voucher dated inside a closed period) is bypassed for this one
    # system-generated closing entry -- see ledger_svc.post_entry.
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
