"""Bank Book balance calculations -- shared between app/routers/
bank_accounts.py (the account list's current balance) and
app/routers/bank_transactions.py (the ledger's running balance and
Bank Reconciliation). See app/models/treasury.py's module docstring
for why this is its own ledger, separate from the General Ledger.
"""
import uuid
from datetime import date
from decimal import Decimal

from sqlalchemy.orm import Session

from app.models.treasury import BankAccount, BankTransaction


def current_balance(db: Session, bank_account: BankAccount, *, as_at: date | None = None) -> Decimal:
    """Opening balance plus every non-voided transaction up to and
    including `as_at` (or all of them, if not given)."""
    query = db.query(BankTransaction).filter(
        BankTransaction.bank_account_id == bank_account.id,
        BankTransaction.is_voided.is_(False),
    )
    if as_at:
        query = query.filter(BankTransaction.transaction_date <= as_at)
    balance = Decimal(bank_account.opening_balance_sgd)
    for txn in query.all():
        balance += Decimal(txn.debit_sgd) - Decimal(txn.credit_sgd)
    return balance


def reconciled_balance(db: Session, bank_account_id: uuid.UUID, opening_balance_sgd: Decimal) -> Decimal:
    """Opening balance plus only the transactions already ticked off
    against a bank statement -- what Bank Reconciliation compares
    against the statement's own closing balance."""
    balance = Decimal(opening_balance_sgd)
    rows = (
        db.query(BankTransaction)
        .filter(
            BankTransaction.bank_account_id == bank_account_id,
            BankTransaction.is_voided.is_(False),
            BankTransaction.is_reconciled.is_(True),
        )
        .all()
    )
    for txn in rows:
        balance += Decimal(txn.debit_sgd) - Decimal(txn.credit_sgd)
    return balance
