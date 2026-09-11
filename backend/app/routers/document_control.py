"""
Document Control -- view and (carefully) adjust the document numbering
counters in app/services/numbering.py, and customize each document
kind's number format (prefix / digit padding / whether the year is
included -- confirmed 2026-09-11).

Editing `last_number` is the one genuinely dangerous action here: set
it too low and the next document raised collides with one already
issued. Changing a format is lower-risk (it can't collide with a
number already issued, since the counter itself is untouched) but
still restricted to FULL access and requires a reason, both recorded
to Event Logs, for the same "this is a deliberate, reasoned change"
posture as adjusting a counter. A format change only affects numbers
issued from that point on -- every document already numbered keeps the
text it was given.
"""
import uuid
from datetime import date

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.models.core import User
from app.models.groups import AccessLevel
from app.schemas.schemas import (
    DocumentNumberFormatOut,
    DocumentNumberFormatUpdate,
    DocumentSequenceOut,
    DocumentSequenceUpdate,
)
from app.services import audit
from app.services.authority import require_module_access
from app.services.numbering import (
    PREFIXES,
    DocumentNumberFormat,
    DocumentSequence,
    format_document_number,
)

router = APIRouter(prefix="/api/document-control", tags=["document-control"])
MODULE = "core_administration"


def _out(db: Session, seq: DocumentSequence) -> DocumentSequenceOut:
    fmt = (
        db.query(DocumentNumberFormat)
        .filter(
            DocumentNumberFormat.company_id == seq.company_id,
            DocumentNumberFormat.doc_kind == seq.doc_kind,
        )
        .first()
    )
    prefix = fmt.prefix if fmt else PREFIXES.get(seq.doc_kind, seq.doc_kind.upper()[:3])
    return DocumentSequenceOut(
        id=seq.id,
        doc_kind=seq.doc_kind,
        prefix=prefix,
        year=seq.year,
        last_number=seq.last_number,
        next_number=format_document_number(
            db, company_id=seq.company_id, doc_kind=seq.doc_kind, year=seq.year, number=seq.last_number + 1
        ),
    )


@router.get("", response_model=list[DocumentSequenceOut])
def list_document_sequences(
    db: Session = Depends(get_db),
    current_user: User = Depends(require_module_access(MODULE, AccessLevel.VIEW)),
):
    rows = (
        db.query(DocumentSequence)
        .filter(DocumentSequence.company_id == current_user.company_id)
        .order_by(DocumentSequence.year.desc(), DocumentSequence.doc_kind)
        .all()
    )
    return [_out(db, r) for r in rows]


@router.patch("/{sequence_id}", response_model=DocumentSequenceOut)
def update_document_sequence(
    sequence_id: uuid.UUID,
    payload: DocumentSequenceUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_module_access(MODULE, AccessLevel.FULL)),
):
    seq = db.get(DocumentSequence, sequence_id)
    if not seq or seq.company_id != current_user.company_id:
        raise HTTPException(status_code=404, detail="Document sequence not found")

    old_number = seq.last_number
    seq.last_number = payload.last_number

    audit.record(
        db,
        entity_type="document_sequence",
        entity_id=seq.id,
        action="last_number_changed",
        actor_user_id=current_user.id,
        reason=payload.reason,
        details=(
            f"{PREFIXES.get(seq.doc_kind, seq.doc_kind.upper()[:3])}-{seq.year}: "
            f"last_number {old_number} -> {payload.last_number}"
        ),
        old_value={"last_number": old_number},
        new_value={"last_number": payload.last_number},
    )
    db.commit()
    db.refresh(seq)
    return _out(db, seq)


def _known_doc_kinds(db: Session, company_id: uuid.UUID) -> list[str]:
    """Every doc_kind this company has ever numbered, plus every kind
    built into the app (PREFIXES) -- so a kind not yet used this year
    (or ever, for a brand-new company) still shows up to customize
    ahead of time, not only after its first document is issued."""
    used = {
        r[0]
        for r in db.query(DocumentSequence.doc_kind)
        .filter(DocumentSequence.company_id == company_id)
        .distinct()
    }
    return sorted(used | set(PREFIXES.keys()))


@router.get("/formats", response_model=list[DocumentNumberFormatOut])
def list_document_number_formats(
    db: Session = Depends(get_db),
    current_user: User = Depends(require_module_access(MODULE, AccessLevel.VIEW)),
):
    overrides = {
        f.doc_kind: f
        for f in db.query(DocumentNumberFormat).filter(
            DocumentNumberFormat.company_id == current_user.company_id
        )
    }
    year = date.today().year
    out = []
    for doc_kind in _known_doc_kinds(db, current_user.company_id):
        fmt = overrides.get(doc_kind)
        if fmt:
            prefix, number_length, include_year, is_custom = (
                fmt.prefix, fmt.number_length, fmt.include_year, True,
            )
        else:
            prefix, number_length, include_year, is_custom = (
                PREFIXES.get(doc_kind, doc_kind.upper()[:3]), 4, True, False,
            )
        out.append(
            DocumentNumberFormatOut(
                doc_kind=doc_kind,
                prefix=prefix,
                number_length=number_length,
                include_year=include_year,
                is_custom=is_custom,
                example=format_document_number(
                    db, company_id=current_user.company_id, doc_kind=doc_kind, year=year, number=1
                ),
            )
        )
    return out


@router.put("/formats/{doc_kind}", response_model=DocumentNumberFormatOut)
def set_document_number_format(
    doc_kind: str,
    payload: DocumentNumberFormatUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_module_access(MODULE, AccessLevel.FULL)),
):
    fmt = (
        db.query(DocumentNumberFormat)
        .filter(
            DocumentNumberFormat.company_id == current_user.company_id,
            DocumentNumberFormat.doc_kind == doc_kind,
        )
        .first()
    )
    old_value = (
        {"prefix": fmt.prefix, "number_length": fmt.number_length, "include_year": fmt.include_year}
        if fmt
        else {
            "prefix": PREFIXES.get(doc_kind, doc_kind.upper()[:3]),
            "number_length": 4,
            "include_year": True,
        }
    )
    if fmt is None:
        fmt = DocumentNumberFormat(company_id=current_user.company_id, doc_kind=doc_kind)
        db.add(fmt)
    fmt.prefix = payload.prefix
    fmt.number_length = payload.number_length
    fmt.include_year = payload.include_year
    db.flush()

    new_value = {
        "prefix": fmt.prefix, "number_length": fmt.number_length, "include_year": fmt.include_year,
    }
    audit.record(
        db,
        entity_type="document_number_format",
        entity_id=fmt.id,
        action="updated",
        actor_user_id=current_user.id,
        reason=payload.reason,
        details=f"{doc_kind}: {old_value} -> {new_value} (applies to numbers issued from now on)",
        old_value=old_value,
        new_value=new_value,
    )
    db.commit()
    db.refresh(fmt)

    year = date.today().year
    return DocumentNumberFormatOut(
        doc_kind=doc_kind,
        prefix=fmt.prefix,
        number_length=fmt.number_length,
        include_year=fmt.include_year,
        is_custom=True,
        example=format_document_number(
            db, company_id=current_user.company_id, doc_kind=doc_kind, year=year, number=1
        ),
    )
