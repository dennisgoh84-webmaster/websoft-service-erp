"""job order status rework and service record deduction fields

Revision ID: a025ca222e9c
Revises: 80a442a466b3
Create Date: 2026-09-11 15:35:10.039597

Confirmed 2026-09-11: Job Order status becomes open/assigned/closed/void
(RESOLVED removed -- auto-close replaces the old manual Resolve step),
plus is_urgent and void_reason. Service Record gains completion_status
('C'/'U'), is_after_hours, and deducted_minutes (the approver's actual
deduction, distinct from the objective rounded_minutes log).

Note: SQLAlchemy's Enum() stores the Python enum MEMBER NAME in
Postgres by default (not .value) -- e.g. job_order_status already holds
'OPEN'/'ASSIGNED'/... uppercase, per the initial migration
(cea09824a3d0). The raw SQL below matches that existing convention.
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'a025ca222e9c'
down_revision: Union[str, Sequence[str], None] = '80a442a466b3'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    # ---- job_orders ----
    op.add_column('job_orders', sa.Column('is_urgent', sa.Boolean(), nullable=False, server_default=sa.false()))
    op.add_column('job_orders', sa.Column('void_reason', sa.String(length=500), nullable=True))
    op.alter_column('job_orders', 'resolved_at', new_column_name='closed_at')

    # Postgres has no ALTER TYPE ... DROP VALUE, so removing RESOLVED
    # (replaced by auto-close, confirmed 2026-09-11) means rebuilding
    # the enum type: create the new shape, migrate existing data (any
    # 'RESOLVED' row becomes 'CLOSED' -- no job order has ever reached
    # RESOLVED in practice, this is a safety net, not an expected
    # migration of real data), then swap the type in.
    op.execute("CREATE TYPE job_order_status_new AS ENUM ('OPEN', 'ASSIGNED', 'CLOSED', 'VOID')")
    op.execute("ALTER TABLE job_orders ALTER COLUMN status DROP DEFAULT")
    op.execute(
        "ALTER TABLE job_orders ALTER COLUMN status TYPE job_order_status_new USING "
        "(CASE status::text WHEN 'RESOLVED' THEN 'CLOSED' ELSE status::text END)::job_order_status_new"
    )
    op.execute("ALTER TABLE job_orders ALTER COLUMN status SET DEFAULT 'OPEN'::job_order_status_new")
    op.execute("DROP TYPE job_order_status")
    op.execute("ALTER TYPE job_order_status_new RENAME TO job_order_status")

    # ---- service_records ----
    op.execute("CREATE TYPE service_record_completion AS ENUM ('COMPLETED', 'UNCOMPLETED')")
    op.add_column(
        'service_records',
        sa.Column(
            'completion_status',
            sa.Enum('COMPLETED', 'UNCOMPLETED', name='service_record_completion'),
            nullable=False,
            server_default='UNCOMPLETED',
        ),
    )
    op.add_column(
        'service_records',
        sa.Column('is_after_hours', sa.Boolean(), nullable=False, server_default=sa.false()),
    )
    op.add_column('service_records', sa.Column('deducted_minutes', sa.Integer(), nullable=True))


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_column('service_records', 'deducted_minutes')
    op.drop_column('service_records', 'is_after_hours')
    op.drop_column('service_records', 'completion_status')
    op.execute("DROP TYPE service_record_completion")

    # Lossy: VOID has no equivalent in the old shape, so any VOID row
    # falls back to OPEN (matches how the router's own reopen action
    # would have restored it anyway).
    op.execute("CREATE TYPE job_order_status_old AS ENUM ('OPEN', 'ASSIGNED', 'RESOLVED', 'CLOSED')")
    op.execute("ALTER TABLE job_orders ALTER COLUMN status DROP DEFAULT")
    op.execute(
        "ALTER TABLE job_orders ALTER COLUMN status TYPE job_order_status_old USING "
        "(CASE status::text WHEN 'VOID' THEN 'OPEN' ELSE status::text END)::job_order_status_old"
    )
    op.execute("ALTER TABLE job_orders ALTER COLUMN status SET DEFAULT 'OPEN'::job_order_status_old")
    op.execute("DROP TYPE job_order_status")
    op.execute("ALTER TYPE job_order_status_old RENAME TO job_order_status")

    op.alter_column('job_orders', 'closed_at', new_column_name='resolved_at')
    op.drop_column('job_orders', 'void_reason')
    op.drop_column('job_orders', 'is_urgent')
