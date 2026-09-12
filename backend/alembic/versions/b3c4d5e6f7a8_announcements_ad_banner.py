"""Announcements + ad banner settings (admin-editable promo content)

Revision ID: b3c4d5e6f7a8
Revises: a7b8c9d0e1f2
Create Date: 2026-09-12

Confirmed 2026-09-12: "is there a place for me to set all these
advertisements or latest updates and push publish" -- adds the
`announcements` table (the "What's New" items shown under the promo
video) and `ad_banner_settings` (a single-row settings table holding
the video URL), replacing what was previously hardcoded in
frontend/src/components/PromoVideoPanel.tsx. Both global, not
company-scoped -- see app/models/announcements.py.

Seeds the settings row and three announcement rows with the exact
content that was hardcoded before this migration, so the banner looks
identical immediately after upgrading; Dennis can then edit/replace
them from the new admin screen.
"""
import uuid

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = "b3c4d5e6f7a8"
down_revision = "a7b8c9d0e1f2"
branch_labels = None
depends_on = None

PREVIOUS_VIDEO_URL = "https://interactive-examples.mdn.mozilla.net/media/cc0-videos/flower.mp4"

PREVIOUS_ITEMS = [
    ("New", "Reference Monitor: break one Chart of Accounts code into named sub-codes for Sales Quotation lines.", 0),
    ("Add-on", "Print/Email/WhatsApp actions are now icon buttons across every document list.", 1),
    ("Update", 'Company/Individual replaces the old "Customer" naming throughout the app.', 2),
]


def upgrade() -> None:
    op.create_table(
        "announcements",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("tag", sa.String(length=30), nullable=True),
        sa.Column("text", sa.Text(), nullable=False),
        sa.Column("sort_order", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()")),
    )

    op.create_table(
        "ad_banner_settings",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("video_url", sa.String(length=1000), nullable=True),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()")),
    )

    announcements = sa.table(
        "announcements",
        sa.column("id", postgresql.UUID(as_uuid=True)),
        sa.column("tag", sa.String),
        sa.column("text", sa.Text),
        sa.column("sort_order", sa.Integer),
    )
    op.bulk_insert(
        announcements,
        [
            {"id": uuid.uuid4(), "tag": tag, "text": text, "sort_order": order}
            for tag, text, order in PREVIOUS_ITEMS
        ],
    )

    settings = sa.table(
        "ad_banner_settings",
        sa.column("id", sa.Integer),
        sa.column("video_url", sa.String),
    )
    op.bulk_insert(settings, [{"id": 1, "video_url": PREVIOUS_VIDEO_URL}])


def downgrade() -> None:
    op.drop_table("ad_banner_settings")
    op.drop_table("announcements")
