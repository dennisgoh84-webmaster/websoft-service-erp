"""Service Record work description (for browser-native grammar-check)

Revision ID: e6f7a8b9c0d1
Revises: d5e6f7a8b9c0
Create Date: 2026-09-12

Confirmed with Dennis, 2026-09-12 (docs/open-business-decisions.md #35):
Service Records previously had no free-text field at all. Adds an
optional work_description, spellchecked in the browser as it's typed --
browser-native only, no AI/external API call.
"""
import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision = "e6f7a8b9c0d1"
down_revision = "d5e6f7a8b9c0"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("service_records", sa.Column("work_description", sa.Text(), nullable=True))


def downgrade() -> None:
    op.drop_column("service_records", "work_description")
