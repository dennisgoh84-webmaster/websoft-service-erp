"""
Setup Lists -- Nationality, Country, State, Area Code, Currency codes.
Global reference data (not scoped to a company) -- see
app/models/setup.py for why one generic table covers all of these.
"""
import uuid

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.models.core import User
from app.models.groups import AccessLevel
from app.models.setup import SetupListItem, SetupListType
from app.schemas.schemas import SetupListItemCreate, SetupListItemOut, SetupListItemUpdate
from app.services import audit, exports
from app.services.authority import require_module_access

router = APIRouter(prefix="/api/setup-lists", tags=["setup-lists"])
MODULE = "core_administration"

SETUP_LIST_EXPORT_FIELDS = ["list_type", "code", "name", "parent_code", "sort_order", "is_active"]


def _filter_items(
    db: Session, list_type: SetupListType | None, include_inactive: bool
) -> list[SetupListItem]:
    query = db.query(SetupListItem)
    if list_type:
        query = query.filter(SetupListItem.list_type == list_type)
    if not include_inactive:
        query = query.filter(SetupListItem.is_active)
    return query.order_by(SetupListItem.list_type, SetupListItem.sort_order, SetupListItem.code).all()


@router.get("", response_model=list[SetupListItemOut])
def list_setup_items(
    list_type: SetupListType | None = None,
    include_inactive: bool = False,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_module_access(MODULE, AccessLevel.VIEW)),
):
    return _filter_items(db, list_type, include_inactive)


def _row(item: SetupListItem) -> dict:
    return {
        "list_type": item.list_type.value,
        "code": item.code,
        "name": item.name,
        "parent_code": item.parent_code or "",
        "sort_order": item.sort_order,
        "is_active": item.is_active,
    }


@router.get("/export.csv")
def export_setup_items_csv(
    list_type: SetupListType | None = None,
    include_inactive: bool = False,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_module_access(MODULE, AccessLevel.VIEW)),
):
    rows = [_row(i) for i in _filter_items(db, list_type, include_inactive)]
    csv_text = exports.rows_to_csv(SETUP_LIST_EXPORT_FIELDS, rows)
    return StreamingResponse(
        iter([csv_text]),
        media_type="text/csv",
        headers={"Content-Disposition": "attachment; filename=setup-lists.csv"},
    )


@router.get("/export.xlsx")
def export_setup_items_excel(
    list_type: SetupListType | None = None,
    include_inactive: bool = False,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_module_access(MODULE, AccessLevel.VIEW)),
):
    rows = [_row(i) for i in _filter_items(db, list_type, include_inactive)]
    data = exports.rows_to_excel(SETUP_LIST_EXPORT_FIELDS, rows, sheet_name="Setup Lists")
    return StreamingResponse(
        iter([data]),
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": "attachment; filename=setup-lists.xlsx"},
    )


@router.post("", response_model=SetupListItemOut)
def create_setup_item(
    payload: SetupListItemCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_module_access(MODULE, AccessLevel.EDIT)),
):
    existing = (
        db.query(SetupListItem)
        .filter(SetupListItem.list_type == payload.list_type, SetupListItem.code == payload.code)
        .first()
    )
    if existing:
        raise HTTPException(
            status_code=409, detail=f"{payload.list_type.value} code {payload.code} already exists."
        )
    item = SetupListItem(**payload.model_dump())
    db.add(item)
    db.flush()
    audit.record(
        db,
        entity_type="setup_list_item",
        entity_id=item.id,
        action="created",
        actor_user_id=current_user.id,
        details=f"{payload.list_type.value}: {payload.code} {payload.name}",
        new_value={"list_type": payload.list_type.value, "code": payload.code, "name": payload.name},
    )
    db.commit()
    db.refresh(item)
    return item


@router.patch("/{item_id}", response_model=SetupListItemOut)
def update_setup_item(
    item_id: uuid.UUID,
    payload: SetupListItemUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_module_access(MODULE, AccessLevel.EDIT)),
):
    item = db.get(SetupListItem, item_id)
    if not item:
        raise HTTPException(status_code=404, detail="Setup list item not found")

    fields = payload.model_dump(exclude_unset=True)
    old_value: dict[str, object] = {}
    new_value: dict[str, object] = {}
    for field in ("code", "name", "parent_code", "sort_order", "is_active"):
        if field not in fields:
            continue
        old = getattr(item, field)
        new = fields[field]
        if old == new:
            continue
        old_value[field] = old
        new_value[field] = new
        setattr(item, field, new)

    audit.record(
        db,
        entity_type="setup_list_item",
        entity_id=item.id,
        action="updated",
        actor_user_id=current_user.id,
        details=f"{item.list_type.value}: {item.code} {item.name}",
        old_value=old_value or None,
        new_value=new_value or None,
    )
    db.commit()
    db.refresh(item)
    return item
