"""Software Task -- see app/models/software_tasks.py for scope/rationale."""
import uuid
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.models.core import User
from app.models.groups import AccessLevel
from app.models.software_tasks import SoftwareTask
from app.schemas.schemas import SoftwareTaskCreate, SoftwareTaskOut, SoftwareTaskUpdate
from app.services import audit, exports
from app.services.authority import require_module_access

router = APIRouter(prefix="/api/software-tasks", tags=["software-tasks"])
MODULE = "software_development"

SOFTWARE_TASK_EXPORT_FIELDS = [
    "title", "modules_affected", "assigned_programmer", "programming_finish_date",
    "programming_hours", "tester", "is_tested",
]


def _task_or_404(db: Session, task_id: uuid.UUID, company_id: uuid.UUID) -> SoftwareTask:
    task = db.get(SoftwareTask, task_id)
    if not task or task.company_id != company_id:
        raise HTTPException(status_code=404, detail="Software task not found")
    return task


def _filter_software_tasks(
    db: Session,
    company_id: uuid.UUID,
    assigned_programmer_id: uuid.UUID | None,
    tester_user_id: uuid.UUID | None,
    untested_only: bool,
) -> list[SoftwareTask]:
    query = db.query(SoftwareTask).filter(SoftwareTask.company_id == company_id)
    if assigned_programmer_id:
        query = query.filter(SoftwareTask.assigned_programmer_id == assigned_programmer_id)
    if tester_user_id:
        query = query.filter(SoftwareTask.tester_user_id == tester_user_id)
    if untested_only:
        query = query.filter(~SoftwareTask.is_tested)
    return query.order_by(SoftwareTask.created_at.desc()).all()


@router.get("", response_model=list[SoftwareTaskOut])
def list_software_tasks(
    assigned_programmer_id: uuid.UUID | None = None,
    tester_user_id: uuid.UUID | None = None,
    untested_only: bool = False,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_module_access(MODULE, AccessLevel.VIEW)),
):
    return _filter_software_tasks(
        db, current_user.company_id, assigned_programmer_id, tester_user_id, untested_only
    )


def _software_task_row(task: SoftwareTask, programmer_name: str, tester_name: str) -> dict:
    return {
        "title": task.title,
        "modules_affected": task.modules_affected or "",
        "assigned_programmer": programmer_name,
        "programming_finish_date": task.programming_finish_date.isoformat() if task.programming_finish_date else "",
        "programming_hours": task.programming_hours if task.programming_hours is not None else "",
        "tester": tester_name,
        "is_tested": task.is_tested,
    }


def _software_tasks_for_export(
    db: Session,
    company_id: uuid.UUID,
    assigned_programmer_id: uuid.UUID | None,
    tester_user_id: uuid.UUID | None,
    untested_only: bool,
) -> list[dict]:
    tasks = _filter_software_tasks(db, company_id, assigned_programmer_id, tester_user_id, untested_only)
    user_ids = {t.assigned_programmer_id for t in tasks if t.assigned_programmer_id} | {
        t.tester_user_id for t in tasks if t.tester_user_id
    }
    user_names = {u.id: u.full_name for u in db.query(User).filter(User.id.in_(user_ids))} if user_ids else {}
    return [
        _software_task_row(
            t,
            user_names.get(t.assigned_programmer_id, "") if t.assigned_programmer_id else "",
            user_names.get(t.tester_user_id, "") if t.tester_user_id else "",
        )
        for t in tasks
    ]


@router.get("/export.csv")
def export_software_tasks_csv(
    assigned_programmer_id: uuid.UUID | None = None,
    tester_user_id: uuid.UUID | None = None,
    untested_only: bool = False,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_module_access(MODULE, AccessLevel.VIEW)),
):
    rows = _software_tasks_for_export(
        db, current_user.company_id, assigned_programmer_id, tester_user_id, untested_only
    )
    csv_text = exports.rows_to_csv(SOFTWARE_TASK_EXPORT_FIELDS, rows)
    return StreamingResponse(
        iter([csv_text]),
        media_type="text/csv",
        headers={"Content-Disposition": "attachment; filename=software-tasks.csv"},
    )


@router.get("/export.xlsx")
def export_software_tasks_excel(
    assigned_programmer_id: uuid.UUID | None = None,
    tester_user_id: uuid.UUID | None = None,
    untested_only: bool = False,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_module_access(MODULE, AccessLevel.VIEW)),
):
    rows = _software_tasks_for_export(
        db, current_user.company_id, assigned_programmer_id, tester_user_id, untested_only
    )
    data = exports.rows_to_excel(SOFTWARE_TASK_EXPORT_FIELDS, rows, sheet_name="Software Tasks")
    return StreamingResponse(
        iter([data]),
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": "attachment; filename=software-tasks.xlsx"},
    )


@router.post("", response_model=SoftwareTaskOut)
def create_software_task(
    payload: SoftwareTaskCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_module_access(MODULE, AccessLevel.EDIT)),
):
    task = SoftwareTask(
        company_id=current_user.company_id,
        created_by_user_id=current_user.id,
        **payload.model_dump(),
    )
    db.add(task)
    db.flush()
    audit.record(
        db,
        entity_type="software_task",
        entity_id=task.id,
        action="created",
        actor_user_id=current_user.id,
        details=f"title={payload.title}",
    )
    db.commit()
    db.refresh(task)
    return task


@router.patch("/{task_id}", response_model=SoftwareTaskOut)
def update_software_task(
    task_id: uuid.UUID,
    payload: SoftwareTaskUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_module_access(MODULE, AccessLevel.EDIT)),
):
    task = _task_or_404(db, task_id, current_user.company_id)
    fields = payload.model_dump(exclude_unset=True)
    old_value: dict[str, object] = {}
    new_value: dict[str, object] = {}
    for field in (
        "title", "description", "modules_affected", "assigned_programmer_id",
        "programming_finish_date", "programming_hours", "tester_user_id",
    ):
        if field not in fields:
            continue
        old = getattr(task, field)
        new = fields[field]
        if old == new:
            continue
        old_value[field] = str(old) if old is not None else None
        new_value[field] = str(new) if new is not None else None
        setattr(task, field, new)

    audit.record(
        db,
        entity_type="software_task",
        entity_id=task.id,
        action="updated",
        actor_user_id=current_user.id,
        old_value=old_value or None,
        new_value=new_value or None,
    )
    db.commit()
    db.refresh(task)
    return task


@router.post("/{task_id}/mark-tested", response_model=SoftwareTaskOut)
def mark_tested(
    task_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_module_access(MODULE, AccessLevel.EDIT)),
):
    task = _task_or_404(db, task_id, current_user.company_id)
    task.is_tested = True
    task.tested_at = datetime.now(timezone.utc)
    audit.record(
        db,
        entity_type="software_task",
        entity_id=task.id,
        action="marked_tested",
        actor_user_id=current_user.id,
    )
    db.commit()
    db.refresh(task)
    return task


@router.post("/{task_id}/reopen-testing", response_model=SoftwareTaskOut)
def reopen_testing(
    task_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_module_access(MODULE, AccessLevel.EDIT)),
):
    task = _task_or_404(db, task_id, current_user.company_id)
    task.is_tested = False
    task.tested_at = None
    audit.record(
        db,
        entity_type="software_task",
        entity_id=task.id,
        action="testing_reopened",
        actor_user_id=current_user.id,
    )
    db.commit()
    db.refresh(task)
    return task
