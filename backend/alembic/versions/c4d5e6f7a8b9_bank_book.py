"""Bank Book: opening balances, bank transactions, bank reconciliation

Revision ID: c4d5e6f7a8b9
Revises: b3c4d5e6f7a8
Create Date: 2026-09-12

Confirmed with Dennis: a Bank Book separate from the General Ledger's
Journal Vouchers -- see app/models/treasury.py's module docstring.
Adds:
- `bank_accounts.opening_balance_sgd` / `opening_balance_date`
- `bank_transactions`: debit/credit entries against a bank account,
  never hard-deleted (voided with a reason instead)
- `bank_reconciliations`: a saved history of each completed
  reconciliation session
"""
import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = "c4d5e6f7a8b9"
down_revision = "b3c4d5e6f7a8"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "bank_accounts",
        sa.Column("opening_balance_sgd", sa.Numeric(14, 2), nullable=False, server_default="0"),
    )
    op.add_column("bank_accounts", sa.Column("opening_balance_date", sa.Date(), nullable=True))

    op.create_table(
        "bank_transactions",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("company_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("bank_account_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("transaction_number", sa.String(length=50), nullable=False),
        sa.Column("transaction_date", sa.Date(), nullable=False),
        sa.Column("description", sa.String(length=500), nullable=False),
        sa.Column("reference", sa.String(length=200), nullable=True),
        sa.Column("debit_sgd", sa.Numeric(14, 2), nullable=False, server_default="0"),
        sa.Column("credit_sgd", sa.Numeric(14, 2), nullable=False, server_default="0"),
        sa.Column("is_reconciled", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.Column("reconciled_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("is_voided", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.Column("void_reason", sa.String(length=500), nullable=True),
        sa.Column("voided_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_by_user_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()")),
        sa.ForeignKeyConstraint(["company_id"], ["companies.id"]),
        sa.ForeignKeyConstraint(["bank_account_id"], ["bank_accounts.id"]),
        sa.ForeignKeyConstraint(["created_by_user_id"], ["users.id"]),
    )
    op.create_index(
        "ix_bank_transactions_bank_account_id", "bank_transactions", ["bank_account_id"]
    )

    op.create_table(
        "bank_reconciliations",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("company_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("bank_account_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("statement_date", sa.Date(), nullable=False),
        sa.Column("statement_balance_sgd", sa.Numeric(14, 2), nullable=False),
        sa.Column("ledger_balance_sgd", sa.Numeric(14, 2), nullable=False),
        sa.Column("difference_sgd", sa.Numeric(14, 2), nullable=False),
        sa.Column("note", sa.Text(), nullable=True),
        sa.Column("reconciled_by_user_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()")),
        sa.ForeignKeyConstraint(["company_id"], ["companies.id"]),
        sa.ForeignKeyConstraint(["bank_account_id"], ["bank_accounts.id"]),
        sa.ForeignKeyConstraint(["reconciled_by_user_id"], ["users.id"]),
    )


def downgrade() -> None:
    op.drop_table("bank_reconciliations")
    op.drop_index("ix_bank_transactions_bank_account_id", table_name="bank_transactions")
    op.drop_table("bank_transactions")
    op.drop_column("bank_accounts", "opening_balance_date")
    op.drop_column("bank_accounts", "opening_balance_sgd")
