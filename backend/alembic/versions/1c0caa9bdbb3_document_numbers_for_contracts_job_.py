"""document numbers for contracts, job orders, service records

Revision ID: 1c0caa9bdbb3
Revises: 4439ad3f1684
Create Date: 2026-09-11 08:15:23.154055

Confirmed 2026-09-11: "all main documents need to have a system
generated running number to be controlled." Contract, Job Order and
Service Record previously had none -- every other document type
(Invoice, Bill, PO, JV, RV, PV, Quotation) already does, via
app/services/numbering.py's per-company-per-year DocumentSequence
counter.

Columns are added nullable first, backfilled here (existing rows get a
number too, oldest first per company/year, exactly like a freshly
issued one would -- CLAUDE.md: never leave existing records without
required data after a migration), THEN set NOT NULL -- the standard
two-step pattern for adding a required column to a table that may
already have rows.

The backfill is deliberately plain SQL rather than importing
app.services.numbering, so this migration keeps working unchanged even
if that service's implementation changes later. It also advances each
company's document_sequences counter to the highest number just
issued, so the next live-issued number continues the sequence instead
of colliding with a backfilled one.
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '1c0caa9bdbb3'
down_revision: Union[str, Sequence[str], None] = '4439ad3f1684'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


# (table, number column, date column to derive the year + ordering from, prefix, doc_kind)
_DOCS = [
    ("contracts", "contract_number", "start_date", "CON", "contract"),
    ("job_orders", "job_order_number", "created_at", "JO", "job_order"),
    ("service_records", "service_record_number", "submitted_at", "SR", "service_record"),
]


def upgrade() -> None:
    """Upgrade schema."""
    bind = op.get_bind()

    op.add_column('contracts', sa.Column('contract_number', sa.String(length=50), nullable=True))
    op.add_column('job_orders', sa.Column('job_order_number', sa.String(length=50), nullable=True))
    op.add_column(
        'service_records', sa.Column('service_record_number', sa.String(length=50), nullable=True)
    )

    for table, number_col, date_col, prefix, doc_kind in _DOCS:
        rows = bind.execute(
            sa.text(f"SELECT id, company_id, {date_col} AS doc_date FROM {table} ORDER BY company_id, doc_date, id")
        ).fetchall()

        # last_number issued so far, per (company_id, year) -- continues
        # from whatever document_sequences already holds for this
        # doc_kind, so a company that already issued live numbers before
        # this migration ran doesn't get collisions.
        counters: dict[tuple, int] = {}
        existing_counters = bind.execute(
            sa.text(
                "SELECT company_id, year, last_number FROM document_sequences WHERE doc_kind = :k"
            ),
            {"k": doc_kind},
        ).fetchall()
        for company_id, year, last_number in existing_counters:
            counters[(company_id, year)] = last_number

        for row in rows:
            year = row.doc_date.year
            key = (row.company_id, year)
            counters[key] = counters.get(key, 0) + 1
            number = f"{prefix}-{year}-{counters[key]:04d}"
            bind.execute(
                sa.text(f"UPDATE {table} SET {number_col} = :number WHERE id = :id"),
                {"number": number, "id": row.id},
            )

        for (company_id, year), last_number in counters.items():
            existing = bind.execute(
                sa.text(
                    "SELECT id FROM document_sequences WHERE company_id = :c AND doc_kind = :k AND year = :y"
                ),
                {"c": company_id, "k": doc_kind, "y": year},
            ).first()
            if existing:
                bind.execute(
                    sa.text("UPDATE document_sequences SET last_number = :n WHERE id = :id"),
                    {"n": last_number, "id": existing.id},
                )
            else:
                bind.execute(
                    sa.text(
                        "INSERT INTO document_sequences (id, company_id, doc_kind, year, last_number) "
                        "VALUES (gen_random_uuid(), :c, :k, :y, :n)"
                    ),
                    {"c": company_id, "k": doc_kind, "y": year, "n": last_number},
                )

    op.alter_column('contracts', 'contract_number', nullable=False)
    op.alter_column('job_orders', 'job_order_number', nullable=False)
    op.alter_column('service_records', 'service_record_number', nullable=False)

    op.create_index(op.f('ix_contracts_contract_number'), 'contracts', ['contract_number'], unique=False)
    op.create_index(op.f('ix_job_orders_job_order_number'), 'job_orders', ['job_order_number'], unique=False)
    op.create_index(
        op.f('ix_service_records_service_record_number'), 'service_records', ['service_record_number'],
        unique=False,
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_index(op.f('ix_service_records_service_record_number'), table_name='service_records')
    op.drop_column('service_records', 'service_record_number')
    op.drop_index(op.f('ix_job_orders_job_order_number'), table_name='job_orders')
    op.drop_column('job_orders', 'job_order_number')
    op.drop_index(op.f('ix_contracts_contract_number'), table_name='contracts')
    op.drop_column('contracts', 'contract_number')
    # Note: document_sequences counters advanced during backfill are not
    # rolled back -- harmless (a counter only ever needs to move
    # forward), and rolling it back risks a future collision if numbers
    # already issued live were kept by the caller of this downgrade.
