"""Add budget overrun approval fields to job_orders

Revision ID: b2c3d4e5f6a7
Revises: a1b2c3d4e5f6
Create Date: 2026-09-12

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = "b2c3d4e5f6a7"
down_revision = "a1b2c3d4e5f6"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "job_orders",
        sa.Column("budget_overrun_approved", sa.Boolean(), nullable=False, server_default=sa.text("false")),
    )
    op.add_column(
        "job_orders",
        sa.Column(
            "budget_overrun_approved_by",
            sa.dialects.postgresql.UUID(as_uuid=True),
            sa.ForeignKey("users.id"),
            nullable=True,
        ),
    )
    op.add_column(
        "job_orders",
        sa.Column("budget_overrun_approved_at", sa.DateTime(timezone=True), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("job_orders", "budget_overrun_approved_at")
    op.drop_column("job_orders", "budget_overrun_approved_by")
    op.drop_column("job_orders", "budget_overrun_approved")
