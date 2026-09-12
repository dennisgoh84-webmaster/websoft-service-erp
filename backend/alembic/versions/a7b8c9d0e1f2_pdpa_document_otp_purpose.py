"""PDPA signed agreement upload + OTP purpose (login vs password_reset)

Revision ID: a7b8c9d0e1f2
Revises: f1a2b3c4d5e6
Create Date: 2026-09-12

Confirmed 2026-09-12:
- "Need to be able to see the signed agreement" -> a new
  `company_individuals.pdpa_agreement_document` column (data URI,
  image or PDF -- see app/routers/company_individuals.py's
  POST .../pdpa-agreement-document).
- "Need to have a forget password, and OTP also" -> `login_otps` gets
  a `purpose` column ("login" | "password_reset") so a login-time code
  can never be replayed to reset a password and vice versa. Existing
  rows (all issued by the login flow so far) backfill to "login".
"""
import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision = "a7b8c9d0e1f2"
down_revision = "f1a2b3c4d5e6"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("company_individuals", sa.Column("pdpa_agreement_document", sa.Text(), nullable=True))

    op.add_column(
        "login_otps",
        sa.Column("purpose", sa.String(length=20), nullable=False, server_default="login"),
    )


def downgrade() -> None:
    op.drop_column("login_otps", "purpose")
    op.drop_column("company_individuals", "pdpa_agreement_document")
