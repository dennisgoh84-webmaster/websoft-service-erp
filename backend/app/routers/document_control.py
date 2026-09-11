"""
Document Control -- view and (carefully) adjust the document numbering
counters in app/services/numbering.py. Editing `last_number` is the one
genuinely dangerous action here: set it too low and the next document
raised collides with one already issued. Restricted to FULL access and
requires a reason, both recorded to Event Logs, rather than a routine
edit.
"""
import uuid

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.models.core import User
from app.models.groups import AccessLevel
from app.schemas.schemas import DocumentSequenceOut, DocumentSequenceUpdate
from app.services import audit
from app.services.authority import require_module_access
from app.services.numbering import PREFIXES, DocumentSequence

router = APIRouter(prefix="/api/document-control", tags=["document-control"])
MODULE = "core_administration"


def _out(seq: DocumentSequence) -> DocumentSequenceOut:
    return DocumentSequenceOut(
        id=seq.id,
        doc_kind=seq.doc_kind,
        prefix=PREFIXES.get(seq.doc_kind, seq.doc_kind.upper()[:3]),
        year=seq.year,
        last_number=seq.last_number,
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
    return [_out(r) for r in rows]


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
    return _out(seq)
