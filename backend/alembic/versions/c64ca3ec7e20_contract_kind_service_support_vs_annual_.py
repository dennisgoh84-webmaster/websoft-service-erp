"""contract kind (service support vs annual), converted annual contract on quotation

Revision ID: c64ca3ec7e20
Revises: 458500193704
Create Date: 2026-09-10 15:32:50.122030

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'c64ca3ec7e20'
down_revision: Union[str, Sequence[str], None] = '458500193704'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    # ---- contracts.contract_kind -------------------------------------
    contract_kind = sa.Enum('SERVICE_SUPPORT', 'ANNUAL', name='contract_kind')
    contract_kind.create(op.get_bind(), checkfirst=True)
    op.add_column('contracts', sa.Column('contract_kind', contract_kind, nullable=True))
    # Every existing contract in this system today is hours-based.
    op.execute("UPDATE contracts SET contract_kind = 'SERVICE_SUPPORT' WHERE contract_kind IS NULL")
    op.alter_column('contracts', 'contract_kind', nullable=False)

    # The 10-hour minimum (SRV-002/012) now applies only to
    # SERVICE_SUPPORT contracts -- an ANNUAL contract has no hours.
    op.drop_constraint('ck_contract_minimum_hours', 'contracts', type_='check')
    op.create_check_constraint(
        'ck_contract_minimum_hours',
        'contracts',
        "contract_kind <> 'SERVICE_SUPPORT' OR contracted_minutes >= 600",
    )

    # ---- quotations.converted_annual_contract_id ----------------------
    op.add_column('quotations', sa.Column('converted_annual_contract_id', sa.UUID(), nullable=True))
    op.create_foreign_key(
        'fk_quotations_converted_annual_contract_id', 'quotations', 'contracts',
        ['converted_annual_contract_id'], ['id'],
    )

    # ---- service_record_outcome: new value for ANNUAL-contract work ---
    with op.get_context().autocommit_block():
        op.execute("ALTER TYPE service_record_outcome ADD VALUE IF NOT EXISTS 'NOT_HOUR_METERED'")


def downgrade() -> None:
    """Downgrade schema."""
    # Postgres cannot drop a single enum value -- downgrading
    # service_record_outcome would require recreating the type, which
    # risks live data using the new value. Left as a manual step.
    op.drop_constraint('fk_quotations_converted_annual_contract_id', 'quotations', type_='foreignkey')
    op.drop_column('quotations', 'converted_annual_contract_id')

    op.drop_constraint('ck_contract_minimum_hours', 'contracts', type_='check')
    op.create_check_constraint(
        'ck_contract_minimum_hours', 'contracts', 'contracted_minutes >= 600',
    )
    op.drop_column('contracts', 'contract_kind')
    sa.Enum(name='contract_kind').drop(op.get_bind(), checkfirst=True)
