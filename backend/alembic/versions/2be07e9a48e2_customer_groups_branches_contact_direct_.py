"""customer groups, branches, contact direct line, memo and billing notes

Revision ID: 2be07e9a48e2
Revises: 923fc61244a0
Create Date: 2026-09-10 13:47:30.830601

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '2be07e9a48e2'
down_revision: Union[str, Sequence[str], None] = '923fc61244a0'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.create_table(
        'customer_groups',
        sa.Column('id', sa.UUID(), nullable=False),
        sa.Column('company_id', sa.UUID(), nullable=False),
        sa.Column('name', sa.String(length=255), nullable=False),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('is_active', sa.Boolean(), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.ForeignKeyConstraint(['company_id'], ['companies.id'], ),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_table(
        'branches',
        sa.Column('id', sa.UUID(), nullable=False),
        sa.Column('customer_id', sa.UUID(), nullable=False),
        sa.Column('branch_code', sa.String(length=50), nullable=True),
        sa.Column('branch_name', sa.String(length=255), nullable=False),
        sa.Column('address_line1', sa.String(length=255), nullable=True),
        sa.Column('address_line2', sa.String(length=255), nullable=True),
        sa.Column('address_city', sa.String(length=100), nullable=True),
        sa.Column('address_state', sa.String(length=100), nullable=True),
        sa.Column('address_postal_code', sa.String(length=20), nullable=True),
        sa.Column('address_country', sa.String(length=100), nullable=True),
        sa.Column('phone', sa.String(length=50), nullable=True),
        sa.Column('is_active', sa.Boolean(), nullable=False),
        sa.ForeignKeyConstraint(['customer_id'], ['customers.id'], ),
        sa.PrimaryKeyConstraint('id'),
    )

    op.add_column('customers', sa.Column('customer_group_id', sa.UUID(), nullable=True))
    op.create_foreign_key(
        'fk_customers_customer_group_id', 'customers', 'customer_groups', ['customer_group_id'], ['id']
    )
    op.add_column('customers', sa.Column('memo', sa.Text(), nullable=True))
    op.add_column('customers', sa.Column('billing_notes', sa.Text(), nullable=True))

    op.add_column('contacts', sa.Column('direct_line', sa.String(length=50), nullable=True))


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_column('contacts', 'direct_line')

    op.drop_column('customers', 'billing_notes')
    op.drop_column('customers', 'memo')
    op.drop_constraint('fk_customers_customer_group_id', 'customers', type_='foreignkey')
    op.drop_column('customers', 'customer_group_id')

    op.drop_table('branches')
    op.drop_table('customer_groups')
