"""Mobile Web App: attachments, signoffs, time_in/time_out

Revision ID: a1b2c3d4e5f6
Revises: f7a8b9c0d1e2
Create Date: 2026-09-12
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "a1b2c3d4e5f6"
down_revision = "f7a8b9c0d1e2"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # 1. Add time_in / time_out to service_records
    op.add_column("service_records", sa.Column("time_in", sa.DateTime(timezone=True), nullable=True))
    op.add_column("service_records", sa.Column("time_out", sa.DateTime(timezone=True), nullable=True))

    # 2. Create attachment_kind enum
    attachment_kind = postgresql.ENUM("WORK_PHOTO", "WORK_VIDEO", "CHOP_PHOTO", name="attachment_kind", create_type=False)
    attachment_kind.create(op.get_bind(), checkfirst=True)

    # 3. Create service_record_attachments table
    op.create_table(
        "service_record_attachments",
        sa.Column("id", sa.UUID(), primary_key=True),
        sa.Column("company_id", sa.UUID(), sa.ForeignKey("companies.id"), nullable=False),
        sa.Column("service_record_id", sa.UUID(), sa.ForeignKey("service_records.id"), nullable=False),
        sa.Column("uploaded_by_user_id", sa.UUID(), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("kind", attachment_kind, nullable=False),
        sa.Column("original_filename", sa.String(500), nullable=False),
        sa.Column("stored_filename", sa.String(500), nullable=False),
        sa.Column("content_type", sa.String(200), nullable=False),
        sa.Column("file_size_bytes", sa.Integer(), nullable=False),
        sa.Column("uploaded_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("is_deleted", sa.Boolean(), nullable=False, server_default=sa.text("false")),
    )
    op.create_index("ix_sr_attachments_sr_id", "service_record_attachments", ["service_record_id"])

    # 4. Create service_record_signoffs table
    op.create_table(
        "service_record_signoffs",
        sa.Column("id", sa.UUID(), primary_key=True),
        sa.Column("company_id", sa.UUID(), sa.ForeignKey("companies.id"), nullable=False),
        sa.Column("service_record_id", sa.UUID(), sa.ForeignKey("service_records.id"), nullable=False, unique=True),
        sa.Column("signer_name", sa.String(255), nullable=False),
        sa.Column("signature_data_uri", sa.Text(), nullable=False),
        sa.Column("chop_attachment_id", sa.UUID(), sa.ForeignKey("service_record_attachments.id"), nullable=True),
        sa.Column("signed_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("signed_by_user_id", sa.UUID(), sa.ForeignKey("users.id"), nullable=False),
    )


def downgrade() -> None:
    op.drop_table("service_record_signoffs")
    op.drop_index("ix_sr_attachments_sr_id", table_name="service_record_attachments")
    op.drop_table("service_record_attachments")

    attachment_kind = postgresql.ENUM("WORK_PHOTO", "WORK_VIDEO", "CHOP_PHOTO", name="attachment_kind", create_type=False)
    attachment_kind.drop(op.get_bind(), checkfirst=True)

    op.drop_column("service_records", "time_out")
    op.drop_column("service_records", "time_in")
