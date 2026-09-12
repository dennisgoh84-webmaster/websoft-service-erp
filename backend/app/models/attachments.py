"""Service Record attachments and sign-off records for the Mobile Web App.

Confirmed 2026-09-12 (planned-work.md #1):
- Photos + videos with no count/size limit, stored as files on disk
- Finger-drawn signature + typed signer name
- Company-chop photo, camera-only capture, auto-watermarked with the
  Service Record number + capture timestamp (the "not allow re-use" rule)
- Sign-off repeats for every Service Record, not once per customer
- Retained permanently (same soft-delete posture as all financial records)
"""
import enum
import uuid
from datetime import datetime

from sqlalchemy import DateTime, Enum, ForeignKey, Integer, String, Text, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


class AttachmentKind(str, enum.Enum):
    """Distinguishes work-evidence photos/videos from the sign-off chop."""
    WORK_PHOTO = "WORK_PHOTO"
    WORK_VIDEO = "WORK_VIDEO"
    CHOP_PHOTO = "CHOP_PHOTO"


class ServiceRecordAttachment(Base):
    """A file (photo or video) attached to a Service Record via the
    mobile web app. Unlimited count per record (confirmed with Dennis).

    Files are stored on disk under UPLOADS_DIR/<company_id>/<record_id>/
    with the attachment id as filename (preserving original extension).
    The chop photo is a special case: it gets an auto-watermark overlay
    stamped at capture time with the SR number + timestamp, and its kind
    is CHOP_PHOTO."""

    __tablename__ = "service_record_attachments"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    company_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("companies.id"), nullable=False)
    service_record_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("service_records.id"), nullable=False, index=True
    )
    uploaded_by_user_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id"), nullable=False)

    kind: Mapped[AttachmentKind] = mapped_column(
        Enum(AttachmentKind, name="attachment_kind"), nullable=False
    )
    original_filename: Mapped[str] = mapped_column(String(500), nullable=False)
    stored_filename: Mapped[str] = mapped_column(String(500), nullable=False)
    content_type: Mapped[str] = mapped_column(String(200), nullable=False)
    file_size_bytes: Mapped[int] = mapped_column(Integer, nullable=False)

    uploaded_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )

    # Soft-delete: never permanently removed (audit-trail rules)
    is_deleted: Mapped[bool] = mapped_column(default=False, nullable=False)


class ServiceRecordSignoff(Base):
    """The customer sign-off on a completed Service Record: a finger-drawn
    signature (stored as a PNG data URI or file), the signer's typed name,
    and the watermarked chop photo (referenced via ServiceRecordAttachment
    with kind=CHOP_PHOTO).

    One sign-off per Service Record. The whole sequence (present record,
    customer signs + states name, photographs chop) repeats for every
    Service Record -- not once per customer."""

    __tablename__ = "service_record_signoffs"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    company_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("companies.id"), nullable=False)
    service_record_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("service_records.id"), nullable=False, unique=True
    )

    signer_name: Mapped[str] = mapped_column(String(255), nullable=False)
    # The drawn signature, stored as a base64 data URI (PNG). Typically
    # small (~20-50KB), so inline storage is fine (same pattern as logos).
    signature_data_uri: Mapped[str] = mapped_column(Text, nullable=False)

    # FK to the chop photo attachment (which has kind=CHOP_PHOTO and
    # carries the watermark overlay)
    chop_attachment_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("service_record_attachments.id"), nullable=True
    )

    signed_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    signed_by_user_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("users.id"), nullable=False
    )
