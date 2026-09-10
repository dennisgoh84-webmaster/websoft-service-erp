"""customer master fields (Odoo-aligned) and contact soft-delete

Revision ID: 923fc61244a0
Revises: fcce9f5d7a06
Create Date: 2026-09-10 13:21:24.766563

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '923fc61244a0'
down_revision: Union[str, Sequence[str], None] = 'fcce9f5d7a06'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    # ---- customers: new master-data fields (Odoo-card alignment) -----
    customer_type = sa.Enum('individual', 'company', name='customer_type')
    customer_type.create(op.get_bind(), checkfirst=True)
    op.add_column('customers', sa.Column('customer_type', customer_type, nullable=True))
    op.add_column('customers', sa.Column('legacy_customer_code', sa.String(length=50), nullable=True))
    op.add_column('customers', sa.Column('contact_person', sa.String(length=255), nullable=True))
    op.add_column('customers', sa.Column('uen', sa.String(length=20), nullable=True))
    op.add_column('customers', sa.Column('gst_registration_no', sa.String(length=50), nullable=True))
    op.add_column('customers', sa.Column('phone', sa.String(length=50), nullable=True))
    op.add_column('customers', sa.Column('mobile', sa.String(length=50), nullable=True))
    op.add_column('customers', sa.Column('website', sa.String(length=255), nullable=True))
    op.add_column('customers', sa.Column('address_line1', sa.String(length=255), nullable=True))
    op.add_column('customers', sa.Column('address_line2', sa.String(length=255), nullable=True))
    op.add_column('customers', sa.Column('address_city', sa.String(length=100), nullable=True))
    op.add_column('customers', sa.Column('address_state', sa.String(length=100), nullable=True))
    op.add_column('customers', sa.Column('address_postal_code', sa.String(length=20), nullable=True))
    op.add_column('customers', sa.Column('address_country', sa.String(length=100), nullable=True))
    op.add_column('customers', sa.Column('tags', sa.String(length=255), nullable=True))
    op.add_column('customers', sa.Column('exclude_auto_sent', sa.Boolean(), nullable=True))
    op.add_column('customers', sa.Column('terms_and_conditions', sa.Text(), nullable=True))

    # Backfill existing (demo) customers: the old single free-text
    # billing_address moves into address_line1 verbatim -- nothing is
    # dropped, it's just reshaped into structured fields. City/state/
    # postal/country for pre-existing rows are left blank rather than
    # guessed by parsing the old free text.
    op.execute("UPDATE customers SET address_line1 = billing_address WHERE billing_address IS NOT NULL")
    # Every existing customer in this system today is a corporate
    # account (name ends "Pte Ltd" etc.) -- backfill customer_type
    # accordingly rather than leaving it ambiguous; new records always
    # set this explicitly going forward.
    op.execute("UPDATE customers SET customer_type = 'company' WHERE customer_type IS NULL")
    op.execute("UPDATE customers SET exclude_auto_sent = false WHERE exclude_auto_sent IS NULL")
    op.alter_column('customers', 'customer_type', nullable=False)
    op.alter_column('customers', 'exclude_auto_sent', nullable=False)

    op.drop_column('customers', 'billing_address')

    # ---- contacts: soft-delete, matching every other master record ---
    op.add_column('contacts', sa.Column('is_active', sa.Boolean(), nullable=True))
    op.execute("UPDATE contacts SET is_active = true WHERE is_active IS NULL")
    op.alter_column('contacts', 'is_active', nullable=False)


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_column('contacts', 'is_active')

    op.add_column('customers', sa.Column('billing_address', sa.Text(), nullable=True))
    op.execute("UPDATE customers SET billing_address = address_line1")

    op.drop_column('customers', 'terms_and_conditions')
    op.drop_column('customers', 'exclude_auto_sent')
    op.drop_column('customers', 'tags')
    op.drop_column('customers', 'address_country')
    op.drop_column('customers', 'address_postal_code')
    op.drop_column('customers', 'address_state')
    op.drop_column('customers', 'address_city')
    op.drop_column('customers', 'address_line2')
    op.drop_column('customers', 'address_line1')
    op.drop_column('customers', 'website')
    op.drop_column('customers', 'mobile')
    op.drop_column('customers', 'phone')
    op.drop_column('customers', 'gst_registration_no')
    op.drop_column('customers', 'uen')
    op.drop_column('customers', 'contact_person')
    op.drop_column('customers', 'legacy_customer_code')
    op.drop_column('customers', 'customer_type')
    sa.Enum(name='customer_type').drop(op.get_bind(), checkfirst=True)
