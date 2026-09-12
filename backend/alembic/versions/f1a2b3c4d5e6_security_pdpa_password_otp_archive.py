"""Security + PDPA: forced password change, email OTP, PDPA consent,
data expiry / soft-archive on Company/Individual

Revision ID: f1a2b3c4d5e6
Revises: 37381fdd5ae6
Create Date: 2026-09-12

Confirmed 2026-09-12 (see app/services/auth.py and
app/routers/company_individuals.py for the full rationale):
- `users.must_change_password`: forces a first-login (and post-admin-
  reset) password change. Defaults true; existing rows are backfilled
  false so nobody already using the system is suddenly locked out.
- `login_otps`: one issued email-OTP challenge per row (see
  app/models/core.py's LoginOtp docstring).
- `company_individuals.pdpa_consent_given` / `pdpa_consent_at`: the
  PDPA-agreement-esigned checkbox + server-stamped date/time.
- `company_individuals.data_expiry_date` / `is_archived` /
  `archived_at`: soft-archive-in-place, same pattern as `is_active`.
"""
import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = "f1a2b3c4d5e6"
down_revision = "37381fdd5ae6"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "users",
        sa.Column("must_change_password", sa.Boolean(), nullable=False, server_default=sa.text("true")),
    )
    # Backfill: nobody already logging in today should be forced through
    # this flow retroactively -- only accounts created/reset after this
    # migration start out true.
    op.execute("UPDATE users SET must_change_password = false")

    op.create_table(
        "login_otps",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("code_hash", sa.String(length=64), nullable=False),
        sa.Column("attempts", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("consumed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()")),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"]),
    )

    op.add_column(
        "company_individuals",
        sa.Column("pdpa_consent_given", sa.Boolean(), nullable=False, server_default=sa.text("false")),
    )
    op.add_column(
        "company_individuals", sa.Column("pdpa_consent_at", sa.DateTime(timezone=True), nullable=True)
    )
    op.add_column("company_individuals", sa.Column("data_expiry_date", sa.Date(), nullable=True))
    op.add_column(
        "company_individuals",
        sa.Column("is_archived", sa.Boolean(), nullable=False, server_default=sa.text("false")),
    )
    op.add_column(
        "company_individuals", sa.Column("archived_at", sa.DateTime(timezone=True), nullable=True)
    )


def downgrade() -> None:
    op.drop_column("company_individuals", "archived_at")
    op.drop_column("company_individuals", "is_archived")
    op.drop_column("company_individuals", "data_expiry_date")
    op.drop_column("company_individuals", "pdpa_consent_at")
    op.drop_column("company_individuals", "pdpa_consent_given")

    op.drop_table("login_otps")

    op.drop_column("users", "must_change_password")
