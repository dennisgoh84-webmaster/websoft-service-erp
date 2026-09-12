"""Platform announcements + the promo video URL shown on the ad banner
(Login page and every page after signing in -- see
frontend/src/components/PromoVideoPanel.tsx). Global, not company-
scoped -- see app/models/announcements.py's module docstring.

GET /public is the one unauthenticated endpoint here (mirrors Company
Setup's GET /api/companies/public-branding): the Login page needs this
before anyone has signed in, and the banner shown after signing in
reads the exact same endpoint rather than a second, authenticated
copy, since the content is identical for everyone and non-sensitive.

Confirmed 2026-09-12: Save = live immediately -- there is no separate
draft/publish step, same as every other admin screen in this system
(Company Setup, Module Control, Tax Types, ...).
"""
import uuid

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.models.announcements import AdBannerSettings, Announcement
from app.models.core import User
from app.models.groups import AccessLevel
from app.schemas.schemas import (
    AdBannerSettingsOut,
    AdBannerSettingsUpdate,
    AnnouncementCreate,
    AnnouncementOut,
    AnnouncementUpdate,
    PublicAdBanner,
)
from app.services import audit
from app.services.authority import require_module_access

router = APIRouter(prefix="/api/announcements", tags=["announcements"])
MODULE = "core_administration"

# Singleton row id for AdBannerSettings (see that model's docstring) --
# and a fixed, arbitrary UUID standing in for it in the audit trail,
# since AuditLogEntry.entity_id is a UUID but this settings row isn't.
SETTINGS_ID = 1
SETTINGS_AUDIT_ID = uuid.UUID(int=SETTINGS_ID)


def _get_or_create_settings(db: Session) -> AdBannerSettings:
    settings = db.get(AdBannerSettings, SETTINGS_ID)
    if not settings:
        settings = AdBannerSettings(id=SETTINGS_ID, video_url=None)
        db.add(settings)
        db.commit()
        db.refresh(settings)
    return settings


def _announcement_or_404(db: Session, announcement_id: uuid.UUID) -> Announcement:
    announcement = db.get(Announcement, announcement_id)
    if not announcement:
        raise HTTPException(status_code=404, detail="Announcement not found")
    return announcement


@router.get("/public", response_model=PublicAdBanner)
def get_public_ad_banner(db: Session = Depends(get_db)):
    settings = _get_or_create_settings(db)
    items = (
        db.query(Announcement)
        .filter(Announcement.is_active)
        .order_by(Announcement.sort_order, Announcement.created_at)
        .all()
    )
    return PublicAdBanner(video_url=settings.video_url, items=items)


@router.get("/settings", response_model=AdBannerSettingsOut)
def get_settings(
    db: Session = Depends(get_db),
    current_user: User = Depends(require_module_access(MODULE, AccessLevel.FULL)),
):
    return _get_or_create_settings(db)


@router.patch("/settings", response_model=AdBannerSettingsOut)
def update_settings(
    payload: AdBannerSettingsUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_module_access(MODULE, AccessLevel.FULL)),
):
    settings = _get_or_create_settings(db)
    old_url = settings.video_url
    settings.video_url = payload.video_url
    audit.record(
        db,
        entity_type="ad_banner_settings",
        entity_id=SETTINGS_AUDIT_ID,
        action="updated",
        actor_user_id=current_user.id,
        old_value={"video_url": old_url},
        new_value={"video_url": payload.video_url},
    )
    db.commit()
    db.refresh(settings)
    return settings


@router.get("", response_model=list[AnnouncementOut])
def list_announcements(
    db: Session = Depends(get_db),
    current_user: User = Depends(require_module_access(MODULE, AccessLevel.VIEW)),
):
    """Every announcement, including inactive ones -- for the admin
    management screen. See GET /public for the filtered, unauthenticated
    view everyone else sees."""
    return db.query(Announcement).order_by(Announcement.sort_order, Announcement.created_at).all()


@router.post("", response_model=AnnouncementOut)
def create_announcement(
    payload: AnnouncementCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_module_access(MODULE, AccessLevel.FULL)),
):
    announcement = Announcement(**payload.model_dump())
    db.add(announcement)
    db.flush()
    audit.record(
        db,
        entity_type="announcement",
        entity_id=announcement.id,
        action="created",
        actor_user_id=current_user.id,
        details=f"text={payload.text}",
    )
    db.commit()
    db.refresh(announcement)
    return announcement


@router.patch("/{announcement_id}", response_model=AnnouncementOut)
def update_announcement(
    announcement_id: uuid.UUID,
    payload: AnnouncementUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_module_access(MODULE, AccessLevel.FULL)),
):
    announcement = _announcement_or_404(db, announcement_id)
    fields = payload.model_dump(exclude_unset=True)
    old_value: dict[str, object] = {}
    new_value: dict[str, object] = {}
    for field, new in fields.items():
        old = getattr(announcement, field)
        if old != new:
            old_value[field] = old
            new_value[field] = new
        setattr(announcement, field, new)

    audit.record(
        db,
        entity_type="announcement",
        entity_id=announcement.id,
        action="updated",
        actor_user_id=current_user.id,
        old_value=old_value or None,
        new_value=new_value or None,
    )
    db.commit()
    db.refresh(announcement)
    return announcement


@router.delete("/{announcement_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_announcement(
    announcement_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_module_access(MODULE, AccessLevel.FULL)),
):
    """A genuine delete, not a soft-delete -- unlike the business/
    financial records CLAUDE.md's "never permanently delete" rule
    covers, an announcement is a marketing blurb with no downstream
    references, so removing a mistaken one outright is reasonable.
    Toggle `is_active` instead to hide one without losing it."""
    announcement = _announcement_or_404(db, announcement_id)
    audit.record(
        db,
        entity_type="announcement",
        entity_id=announcement.id,
        action="deleted",
        actor_user_id=current_user.id,
        details=f"text={announcement.text}",
    )
    db.delete(announcement)
    db.commit()
