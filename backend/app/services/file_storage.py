"""Local-disk file storage for Service Record attachments.

Files are stored under UPLOADS_DIR/<company_id>/<service_record_id>/
with the attachment UUID as filename (preserving original extension).
In Docker this directory is a named volume that persists across restarts.

The chop-photo watermark stamps the Service Record number + capture
timestamp visibly on the image at save time, enforcing the "no re-use"
rule (planned-work.md #1, confirmed 2026-09-12: camera-only + watermark).
"""
import os
import uuid
from datetime import datetime
from io import BytesIO
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

from app.core.config import settings


def _ensure_dir(path: Path) -> None:
    path.mkdir(parents=True, exist_ok=True)


def upload_dir_for(company_id: uuid.UUID, service_record_id: uuid.UUID) -> Path:
    d = Path(settings.uploads_dir) / str(company_id) / str(service_record_id)
    _ensure_dir(d)
    return d


def save_file(
    company_id: uuid.UUID,
    service_record_id: uuid.UUID,
    attachment_id: uuid.UUID,
    original_filename: str,
    data: bytes,
) -> str:
    """Save raw bytes to disk. Returns the stored filename."""
    ext = Path(original_filename).suffix.lower() or ""
    stored_name = f"{attachment_id}{ext}"
    dest = upload_dir_for(company_id, service_record_id) / stored_name
    dest.write_bytes(data)
    return stored_name


def get_file_path(
    company_id: uuid.UUID,
    service_record_id: uuid.UUID,
    stored_filename: str,
) -> Path | None:
    p = Path(settings.uploads_dir) / str(company_id) / str(service_record_id) / stored_filename
    return p if p.is_file() else None


def watermark_chop_photo(
    image_bytes: bytes,
    service_record_number: str,
    timestamp: datetime,
) -> bytes:
    """Stamp a visible watermark on the chop photo with the SR number
    and capture date/time. Returns the watermarked image as JPEG bytes.

    The watermark is semi-transparent, placed diagonally across the
    center, plus a bottom strip with the SR number and timestamp --
    making the photo uniquely tied to this one Service Record."""
    img = Image.open(BytesIO(image_bytes)).convert("RGBA")

    # Create overlay for the watermark text
    overlay = Image.new("RGBA", img.size, (0, 0, 0, 0))
    draw = ImageDraw.Draw(overlay)

    # Build watermark text
    ts_str = timestamp.strftime("%Y-%m-%d %H:%M:%S")
    watermark_text = f"{service_record_number}  |  {ts_str}"

    # Calculate font size relative to image width (roughly 3% of width)
    font_size = max(16, img.width // 30)
    try:
        font = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", font_size)
    except (OSError, IOError):
        font = ImageFont.load_default()

    # Bottom strip watermark
    bbox = draw.textbbox((0, 0), watermark_text, font=font)
    text_w = bbox[2] - bbox[0]
    text_h = bbox[3] - bbox[1]

    strip_h = text_h + 20
    strip_y = img.height - strip_h

    # Semi-transparent black strip at the bottom
    draw.rectangle(
        [(0, strip_y), (img.width, img.height)],
        fill=(0, 0, 0, 160),
    )
    # White text centered in the strip
    text_x = (img.width - text_w) // 2
    text_y = strip_y + 10
    draw.text((text_x, text_y), watermark_text, fill=(255, 255, 255, 230), font=font)

    # Diagonal watermark across the center (larger, more transparent)
    diag_font_size = max(24, img.width // 15)
    try:
        diag_font = ImageFont.truetype(
            "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", diag_font_size
        )
    except (OSError, IOError):
        diag_font = font

    diag_text = service_record_number
    dbbox = draw.textbbox((0, 0), diag_text, font=diag_font)
    dw = dbbox[2] - dbbox[0]
    dh = dbbox[3] - dbbox[1]
    dx = (img.width - dw) // 2
    dy = (img.height - dh) // 2 - strip_h // 2

    # Semi-transparent white diagonal text
    draw.text((dx, dy), diag_text, fill=(255, 255, 255, 80), font=diag_font)

    # Composite overlay onto original
    result = Image.alpha_composite(img, overlay).convert("RGB")

    out = BytesIO()
    result.save(out, format="JPEG", quality=90)
    return out.getvalue()


def delete_file(
    company_id: uuid.UUID,
    service_record_id: uuid.UUID,
    stored_filename: str,
) -> None:
    """Best-effort file deletion (soft-delete in DB is the real gate)."""
    p = Path(settings.uploads_dir) / str(company_id) / str(service_record_id) / stored_filename
    try:
        p.unlink(missing_ok=True)
    except OSError:
        pass
