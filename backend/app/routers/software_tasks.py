"""Software Task -- see app/models/software_tasks.py for scope/rationale."""
import uuid
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.models.core import User
from app.models.groups import AccessLevel
from app.models.software_tasks import SoftwareTask
from app.schemas.schemas import SoftwareTaskCreate, SoftwareTaskOut, SoftwareTaskUpdate
from app.services import audit
from app.services.authority import require_module_access

router = APIRouter(prefix="/api/software-tasks", tags=["software-tasks"])
MODULE = "software_development"


def _task_or_404(db: Session, task_id: uuid.UUID, company_id: uuid.UUID) -> SoftwareTask:
    task = db.get(SoftwareTask, task_id)
    if not task or task.company_id != company_id:
        raise HTTPException(status_code=404, detail="Software task not found")
    return task


@router.get("", response_model=list[SoftwareTaskOut])
def list_software_tasks(
    assigned_programmer_id: uuid.UUID | None = None,
    tester_user_id: uuid.UUID | None = None,
    untested_only: bool = False,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_module_access(MODULE, AccessLevel.VIEW)),
):
    query = db.query(SoftwareTask).filter(SoftwareTask.company_id == current_user.company_id)
    if assigned_programmer_id:
        query = query.filter(SoftwareTask.assigned_programmer_id == assigned_programmer_id)
    if tester_user_id:
        query = query.filter(SoftwareTask.tester_user_id == tester_user_id)
    if untested_only:
        query = query.filter(~SoftwareTask.is_tested)
    return query.order_by(SoftwareTask.created_at.desc()).all()


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
