"""company-scope job orders, service records, excess usage, invoices

Revision ID: 051c0726fa57
Revises: 24cc1861aed5
Create Date: 2026-09-10 03:04:04.442305

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '051c0726fa57'
down_revision: Union[str, Sequence[str], None] = '24cc1861aed5'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Add company_id to the four remaining company-owned tables.

    These tables hold existing business records, so the column is added
    nullable, backfilled from the record each row already hangs off
    (job order -> customer, invoice -> customer, service record -> job
    order, excess usage -> contract), and only then made NOT NULL.
    Adding it NOT NULL in one step would fail on a populated table.
    """
    # 1. Add nullable.
    op.add_column('job_orders', sa.Column('company_id', sa.UUID(), nullable=True))
    op.add_column('invoices', sa.Column('company_id', sa.UUID(), nullable=True))
    op.add_column('service_records', sa.Column('company_id', sa.UUID(), nullable=True))
    op.add_column('excess_usage_records', sa.Column('company_id', sa.UUID(), nullable=True))

    # 2. Backfill from the owning record.
    op.execute(
        "UPDATE job_orders jo SET company_id = c.company_id "
        "FROM customers c WHERE c.id = jo.customer_id"
    )
    op.execute(
        "UPDATE invoices i SET company_id = c.company_id "
        "FROM customers c WHERE c.id = i.customer_id"
    )
    # service_records depends on job_orders being backfilled first.
    op.execute(
        "UPDATE service_records sr SET company_id = jo.company_id "
        "FROM job_orders jo WHERE jo.id = sr.job_order_id"
    )
    op.execute(
        "UPDATE excess_usage_records eur SET company_id = ct.company_id "
        "FROM contracts ct WHERE ct.id = eur.contract_id"
    )

    # 3. Now enforce NOT NULL + the foreign keys.
    op.alter_column('job_orders', 'company_id', nullable=False)
    op.alter_column('invoices', 'company_id', nullable=False)
    op.alter_column('service_records', 'company_id', nullable=False)
    op.alter_column('excess_usage_records', 'company_id', nullable=False)

    op.create_foreign_key(
        'fk_job_orders_company', 'job_orders', 'companies', ['company_id'], ['id']
    )
    op.create_foreign_key('fk_invoices_company', 'invoices', 'companies', ['company_id'], ['id'])
    op.create_foreign_key(
        'fk_service_records_company', 'service_records', 'companies', ['company_id'], ['id']
    )
    op.create_foreign_key(
        'fk_excess_usage_records_company',
        'excess_usage_records',
        'companies',
        ['company_id'],
        ['id'],
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_constraint('fk_service_records_company', 'service_records', type_='foreignkey')
    op.drop_column('service_records', 'company_id')
    op.drop_constraint('fk_job_orders_company', 'job_orders', type_='foreignkey')
    op.drop_column('job_orders', 'company_id')
    op.drop_constraint('fk_invoices_company', 'invoices', type_='foreignkey')
    op.drop_column('invoices', 'company_id')
    op.drop_constraint(
        'fk_excess_usage_records_company', 'excess_usage_records', type_='foreignkey'
    )
    op.drop_column('excess_usage_records', 'company_id')
