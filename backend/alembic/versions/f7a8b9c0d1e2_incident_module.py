"""Incident Module

Revision ID: f7a8b9c0d1e2
Revises: e6f7a8b9c0d1
Create Date: 2026-09-12

Confirmed with Dennis (docs/open-business-decisions.md #36): the
front-door call/email log that routes into a Quotation, Job Order, or
Software Task (each conversion creates the real record, not just an
assignment), with a plain status+assignee for "someone to return the
call" -- no separate reminder record.
"""
import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = "f7a8b9c0d1e2"
down_revision = "e6f7a8b9c0d1"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "incidents",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("company_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("incident_number", sa.String(length=50), nullable=False),
        sa.Column("customer_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column(
            "source",
            sa.Enum("PHONE", "EMAIL", "OTHER", name="incident_source"),
            nullable=False,
            server_default="PHONE",
        ),
        sa.Column("subject", sa.String(length=255), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("sender_name", sa.String(length=255), nullable=True),
        sa.Column("sender_email", sa.String(length=255), nullable=True),
        sa.Column("sender_phone", sa.String(length=50), nullable=True),
        sa.Column(
            "status",
            sa.Enum("OPEN", "PENDING_CALLBACK", "CONVERTED", "CLOSED", name="incident_status"),
            nullable=False,
            server_default="OPEN",
        ),
        sa.Column("assigned_to_user_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("converted_quotation_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("converted_job_order_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("converted_software_task_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("close_reason", sa.String(length=500), nullable=True),
        sa.Column("closed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("closed_by_user_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("created_by_user_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()")),
        sa.ForeignKeyConstraint(["company_id"], ["companies.id"]),
        sa.ForeignKeyConstraint(["customer_id"], ["company_individuals.id"]),
        sa.ForeignKeyConstraint(["assigned_to_user_id"], ["users.id"]),
        sa.ForeignKeyConstraint(["converted_quotation_id"], ["quotations.id"]),
        sa.ForeignKeyConstraint(["converted_job_order_id"], ["job_orders.id"]),
        sa.ForeignKeyConstraint(["converted_software_task_id"], ["software_tasks.id"]),
        sa.ForeignKeyConstraint(["closed_by_user_id"], ["users.id"]),
        sa.ForeignKeyConstraint(["created_by_user_id"], ["users.id"]),
    )
    op.create_index("ix_incidents_incident_number", "incidents", ["incident_number"])


def downgrade() -> None:
    op.drop_index("ix_incidents_incident_number", table_name="incidents")
    op.drop_table("incidents")
    op.execute("DROP TYPE IF EXISTS incident_status")
    op.execute("DROP TYPE IF EXISTS incident_source")
