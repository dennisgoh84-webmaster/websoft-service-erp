"""Platform announcements shown on the advertisement/promo video banner
(Login page and every page after signing in -- see
frontend/src/components/PromoVideoPanel.tsx). Global, not company-
scoped: these are announcements about the software itself (new
features, updates), not a per-company message, and the Login page
shows them before any company has even been selected -- same reasoning
as Company Setup's GET /api/companies/public-branding.

Confirmed 2026-09-12: "is there a place for me to set all these
advertisements or latest updates and push publish" -- built as
Save = live immediately (matches every other admin screen in this
system), so there is no separate draft/publish step.
"""
import uuid
from datetime import datetime

from sqlalchemy import Boolean, DateTime, Integer, String, Text, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


class Announcement(Base):
    """One "What's New" item shown under the promo video -- a short tag
    (e.g. "New", "Update") plus a one-line message, same idea as the
    original hardcoded PROMO_ITEMS this replaces. Soft-delete
    (`is_active`) follows this system's usual convention, though a
    genuine delete is also offered from the admin screen since these
    are marketing blurbs, not audited business/financial records."""

    __tablename__ = "announcements"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tag: Mapped[str | None] = mapped_column(String(30), nullable=True)
    text: Mapped[str] = mapped_column(Text, nullable=False)
    sort_order: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class AdBannerSettings(Base):
    """A single-row settings table holding the promo video URL (see
    PromoVideoPanel.tsx). Singleton pattern: app/routers/announcements.py
    always reads/creates the one row with a fixed id (1) rather than
    filtering a list, since there is exactly one video slot to manage.
    A URL, not an uploaded file: a video is far too large to hold
    inline the way Company.logo/User.photo do, and this system has no
    video-hosting infrastructure -- see
    docs/open-business-decisions.md #28.3."""

    __tablename__ = "ad_banner_settings"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    video_url: Mapped[str | None] = mapped_column(String(1000), nullable=True)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )
