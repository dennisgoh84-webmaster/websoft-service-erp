"""Job Order type (SUPPORT/PROJECT) + project milestones table

Revision ID: d4e5f6a7b8c9
Revises: c3d4e5f6a7b8
Create Date: 2026-09-12

Adds:
- job_order_type enum (support, project)
- job_order_type column on job_orders (default 'support')
- milestone_type enum
- milestone_status enum
- project_milestones table
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID


revision = "d4e5f6a7b8c9"
down_revision = "c3d4e5f6a7b8"
branch_labels = None
depends_on = None

JOB_ORDER_TYPES = ["support", "project"]
MILESTONE_TYPES = [
    "installation", "training", "repeat_training",
    "handover", "completion_signoff",
]
MILESTONE_STATUSES = ["pending", "in_progress", "completed", "skipped"]


def upgrade() -> None:
    # ── Enums ──────────────────────────────────────────────────────
    job_order_type = sa.Enum(*JOB_ORDER_TYPES, name="job_order_type")
    job_order_type.create(op.get_bind(), checkfirst=True)

    milestone_type = sa.Enum(*MILESTONE_TYPES, name="milestone_type")
    milestone_type.create(op.get_bind(), checkfirst=True)

    milestone_status = sa.Enum(*MILESTONE_STATUSES, name="milestone_status")
    milestone_status.create(op.get_bind(), checkfirst=True)

    # ── Add job_order_type column to job_orders ───────────────────
    op.add_column(
        "job_orders",
        sa.Column(
            "job_order_type",
            sa.Enum(*JOB_ORDER_TYPES, name="job_order_type", create_type=False),
            nullable=False,
            server_default="support",
        ),
    )

    # ── project_milestones ────────────────────────────────────────
    op.create_table(
        "project_milestones",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "job_order_id", UUID(as_uuid=True),
            sa.ForeignKey("job_orders.id"), nullable=False, index=True,
        ),
        sa.Column(
            "milestone_type",
            sa.Enum(*MILESTONE_TYPES, name="milestone_type", create_type=False),
            nullable=False,
        ),
        sa.Column("label", sa.String(200), nullable=False),
        sa.Column("sort_order", sa.Integer, nullable=False, server_default="0"),
        sa.Column("planned_start", sa.Date, nullable=True),
        sa.Column("planned_end", sa.Date, nullable=True),
        sa.Column("actual_start", sa.Date, nullable=True),
        sa.Column("actual_end", sa.Date, nullable=True),
        sa.Column(
            "assigned_user_id", UUID(as_uuid=True),
            sa.ForeignKey("users.id"), nullable=True,
        ),
        sa.Column(
            "status",
            sa.Enum(*MILESTONE_STATUSES, name="milestone_status", create_type=False),
            nullable=False,
            server_default="pending",
        ),
        sa.Column("notes", sa.Text, nullable=True),
        sa.Column(
            "created_at", sa.DateTime(timezone=True),
            server_default=sa.func.now(),
        ),
    )


def downgrade() -> None:
    op.drop_table("project_milestones")
    op.drop_column("job_orders", "job_order_type")

    sa.Enum(name="milestone_status").drop(op.get_bind(), checkfirst=True)
    sa.Enum(name="milestone_type").drop(op.get_bind(), checkfirst=True)
    sa.Enum(name="job_order_type").drop(op.get_bind(), checkfirst=True)
