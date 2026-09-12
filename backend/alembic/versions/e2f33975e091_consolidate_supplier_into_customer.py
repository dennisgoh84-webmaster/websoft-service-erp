"""consolidate supplier into customer

2026-09-12: "when talking about supplier, remember to use the same
company/individual file, do not add or reinvent a new one again" -- the
standalone `suppliers` table is folded into `customers` as a role flag
(`is_supplier`), alongside the existing `is_customer` (defaults True --
that's what every existing customers row already was).

Each migrated supplier keeps its original id, so purchase_orders /
supplier_invoices / supplier_payments.supplier_id keeps pointing at the
right row without rewriting a single value on those tables -- only the
foreign key's target table changes, from suppliers to customers.

Revision ID: e2f33975e091
Revises: ca1ddfca6a83
Create Date: 2026-09-12 00:53:47.614188

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = 'e2f33975e091'
down_revision: Union[str, Sequence[str], None] = 'ca1ddfca6a83'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Role flags on Customer -- backfilled via server_default so the
    # existing (all is_customer=True) rows stay valid under NOT NULL.
    op.add_column(
        'customers',
        sa.Column('is_customer', sa.Boolean(), nullable=False, server_default=sa.text('true')),
    )
    op.add_column(
        'customers',
        sa.Column('is_supplier', sa.Boolean(), nullable=False, server_default=sa.text('false')),
    )

    # Copy every supplier into customers, same id, is_supplier=True,
    # is_customer=False (nothing here was ever a customer). Supplier had
    # a single free-text `address` column; customers has structured
    # address_line1/2/city/.../country, so the whole string lands in
    # address_line1 rather than being split up by guesswork.
    op.execute(
        """
        INSERT INTO customers (
            id, company_id, customer_type, name, gst_registration_no,
            billing_email, phone, address_line1, payment_terms_days,
            exclude_auto_sent, is_customer, is_supplier, is_active, created_at
        )
        SELECT
            id, company_id, 'company', name, gst_registration_no,
            email, phone, address, payment_terms_days,
            false, false, true, is_active, created_at
        FROM suppliers
        """
    )

    # Repoint the FKs at customers -- the data migration above means
    # every existing supplier_id value already exists in customers.id.
    op.drop_constraint(op.f('purchase_orders_supplier_id_fkey'), 'purchase_orders', type_='foreignkey')
    op.create_foreign_key(None, 'purchase_orders', 'customers', ['supplier_id'], ['id'])
    op.drop_constraint(op.f('supplier_invoices_supplier_id_fkey'), 'supplier_invoices', type_='foreignkey')
    op.create_foreign_key(None, 'supplier_invoices', 'customers', ['supplier_id'], ['id'])
    op.drop_constraint(op.f('supplier_payments_supplier_id_fkey'), 'supplier_payments', type_='foreignkey')
    op.create_foreign_key(None, 'supplier_payments', 'customers', ['supplier_id'], ['id'])

    op.drop_table('suppliers')


def downgrade() -> None:
    """Best-effort reversal. A customer record that was ticked both
    is_customer AND is_supplier after the merge (a contact who is both)
    downgrades to a supplier row that has lost any customer-only fields
    -- there is no way to know which fields were "supplier" data versus
    later customer edits, so this is not attempted; such records are
    left as customers only and simply won't reappear in `suppliers`."""
    op.create_table(
        'suppliers',
        sa.Column('id', sa.UUID(), autoincrement=False, nullable=False),
        sa.Column('company_id', sa.UUID(), autoincrement=False, nullable=False),
        sa.Column('name', sa.VARCHAR(length=255), autoincrement=False, nullable=False),
        sa.Column('email', sa.VARCHAR(length=255), autoincrement=False, nullable=True),
        sa.Column('address', sa.TEXT(), autoincrement=False, nullable=True),
        sa.Column('gst_registration_no', sa.VARCHAR(length=50), autoincrement=False, nullable=True),
        sa.Column('payment_terms_days', sa.INTEGER(), autoincrement=False, nullable=True),
        sa.Column('is_active', sa.BOOLEAN(), autoincrement=False, nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), autoincrement=False, nullable=False),
        sa.Column('phone', sa.VARCHAR(length=50), autoincrement=False, nullable=True),
        sa.ForeignKeyConstraint(['company_id'], ['companies.id'], name=op.f('suppliers_company_id_fkey')),
        sa.PrimaryKeyConstraint('id', name=op.f('suppliers_pkey')),
    )

    op.execute(
        """
        INSERT INTO suppliers (id, company_id, name, email, address, gst_registration_no,
                                payment_terms_days, is_active, created_at, phone)
        SELECT id, company_id, name, billing_email, address_line1, gst_registration_no,
               payment_terms_days, is_active, created_at, phone
        FROM customers WHERE is_supplier = true
        """
    )

    op.drop_constraint(None, 'supplier_payments', type_='foreignkey')
    op.create_foreign_key(op.f('supplier_payments_supplier_id_fkey'), 'supplier_payments', 'suppliers', ['supplier_id'], ['id'])
    op.drop_constraint(None, 'supplier_invoices', type_='foreignkey')
    op.create_foreign_key(op.f('supplier_invoices_supplier_id_fkey'), 'supplier_invoices', 'suppliers', ['supplier_id'], ['id'])
    op.drop_constraint(None, 'purchase_orders', type_='foreignkey')
    op.create_foreign_key(op.f('purchase_orders_supplier_id_fkey'), 'purchase_orders', 'suppliers', ['supplier_id'], ['id'])

    op.execute("DELETE FROM customers WHERE is_supplier = true AND is_customer = false")
    op.drop_column('customers', 'is_supplier')
    op.drop_column('customers', 'is_customer')
