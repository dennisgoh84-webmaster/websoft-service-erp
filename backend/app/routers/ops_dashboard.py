"""Ops Dashboard: a personal, freeform task tracker per staff member --
see app/models/ops_tasks.py for the confirmed scope and the 2026-09-11
decision record in docs/open-business-decisions.md.
"""
import uuid

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.models.core import User, UserRole
from app.models.groups import AccessLevel
from app.models.job_orders import JobOrder, JobOrderStatus
from app.models.ops_tasks import OpsTask, OpsTaskCategory, OpsTaskStatus
from app.models.software_tasks import SoftwareTask
from app.schemas.schemas import (
    OpsDashboardCategoryOut,
    OpsDashboardOut,
    OpsRollupJobOrderOut,
    OpsRollupSoftwareTaskOut,
    OpsTaskCategoryCreate,
    OpsTaskCategoryOut,
    OpsTaskCreate,
    OpsTaskOut,
    OpsTaskUpdate,
)
from app.services import audit
from app.services.authority import require_module_access

router = APIRouter(prefix="/api/ops-dashboard", tags=["ops-dashboard"])
MODULE = "ops_dashboard"

# Confirmed 2026-09-11: everyone sees only their own dashboard by
# default; Owner/Service Lead/Sales Manager can also view AND edit
# another staff member's dashboard for oversight. Mirrors the
# "manager-ish" role set already used for Service Record approval and
# Excess Review.
MANAGER_ROLES = {UserRole.OWNER, UserRole.SERVICE_LEAD, UserRole.SALES_MANAGER}


def _is_manager(user: User) -> bool:
    return user.role in MANAGER_ROLES


def _target_user(db: Session, current_user: User, staff_id: uuid.UUID | None) -> User:
    """Resolve whose dashboard/category/task is being acted on. Any
    staff member may act on their own; only a manager may act on
    someone else's."""
    if staff_id is None or staff_id == current_user.id:
        return current_user
    if not _is_manager(current_user):
        raise HTTPException(status_code=403, detail="Only the owner, service lead, or sales manager can view or edit another staff member's dashboard.")
    target = db.get(User, staff_id)
    if not target or target.company_id != current_user.company_id:
        raise HTTPException(status_code=404, detail="Staff member not found")
    return target


def _task_out(t: OpsTask, staff_names: dict[uuid.UUID, str]) -> OpsTaskOut:
    return OpsTaskOut(
        id=t.id,
        category_id=t.category_id,
        owner_user_id=t.owner_user_id,
        title=t.title,
        status=t.status,
        next_action=t.next_action,
        owner_label=t.owner_label,
        due_label=t.due_label,
        follow_up_staff_id=t.follow_up_staff_id,
        follow_up_staff_name=staff_names.get(t.follow_up_staff_id) if t.follow_up_staff_id else None,
        follow_up_date=t.follow_up_date,
        is_sample=t.is_sample,
    )


@router.get("", response_model=OpsDashboardOut)
def get_dashboard(
    staff_id: uuid.UUID | None = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_module_access(MODULE, AccessLevel.VIEW)),
):
    staff = _target_user(db, current_user, staff_id)

    categories = (
        db.query(OpsTaskCategory)
        .filter(OpsTaskCategory.company_id == current_user.company_id)
        .filter(OpsTaskCategory.owner_user_id == staff.id)
        .filter(OpsTaskCategory.is_active)
        .order_by(OpsTaskCategory.sort_order, OpsTaskCategory.created_at)
        .all()
    )
    tasks = (
        db.query(OpsTask)
        .filter(OpsTask.company_id == current_user.company_id)
        .filter(OpsTask.owner_user_id == staff.id)
        .filter(OpsTask.is_active)
        .order_by(OpsTask.created_at)
        .all()
    ) if categories else []

    staff_ids = {t.follow_up_staff_id for t in tasks if t.follow_up_staff_id}
    staff_names = {u.id: u.full_name for u in db.query(User).filter(User.id.in_(staff_ids))} if staff_ids else {}

    tasks_by_category: dict[uuid.UUID, list[OpsTask]] = {}
    for t in tasks:
        tasks_by_category.setdefault(t.category_id, []).append(t)

    category_out = [
        OpsDashboardCategoryOut(
            category=OpsTaskCategoryOut.model_validate(c),
            tasks=[_task_out(t, staff_names) for t in tasks_by_category.get(c.id, [])],
        )
        for c in categories
    ]

    total = len(tasks)
    open_count = sum(1 for t in tasks if t.status == OpsTaskStatus.NOT_STARTED)
    in_progress_count = sum(1 for t in tasks if t.status in (OpsTaskStatus.IN_PROGRESS, OpsTaskStatus.WATCH))
    blocked_count = sum(1 for t in tasks if t.status == OpsTaskStatus.BLOCKED)
    done_count = sum(1 for t in tasks if t.status == OpsTaskStatus.DONE)

    # Real-ERP-data rollup (confirmed 2026-09-11: "auto-populate from
    # real ERP data" alongside the freeform tasks above) -- read-only,
    # no new model, just filtered reads of what already exists.
    my_job_orders = (
        db.query(JobOrder)
        .filter(JobOrder.company_id == current_user.company_id)
        .filter(JobOrder.assigned_to_user_id == staff.id)
        .filter(JobOrder.status.in_([JobOrderStatus.OPEN, JobOrderStatus.ASSIGNED]))
        .order_by(JobOrder.due_date.asc().nulls_last(), JobOrder.created_at.desc())
        .all()
    )
    my_software_tasks_rows: list[OpsRollupSoftwareTaskOut] = []
    for role_label, column in (("Programmer", SoftwareTask.assigned_programmer_id), ("Tester", SoftwareTask.tester_user_id)):
        rows = (
            db.query(SoftwareTask)
            .filter(SoftwareTask.company_id == current_user.company_id)
            .filter(column == staff.id)
            .filter(SoftwareTask.is_tested.is_(False))
            .order_by(SoftwareTask.created_at.desc())
            .all()
        )
        for r in rows:
            my_software_tasks_rows.append(
                OpsRollupSoftwareTaskOut(id=r.id, title=r.title, role=role_label, is_tested=r.is_tested)
            )

    return OpsDashboardOut(
        staff_id=staff.id,
        staff_name=staff.full_name,
        can_view_others=_is_manager(current_user),
        categories=category_out,
        total_tasks=total,
        open_count=open_count,
        in_progress_count=in_progress_count,
        blocked_count=blocked_count,
        done_count=done_count,
        my_job_orders=[
            OpsRollupJobOrderOut(id=jo.id, job_order_number=jo.job_order_number, subject=jo.subject, status=jo.status.value, due_date=jo.due_date)
            for jo in my_job_orders
        ],
        my_software_tasks=my_software_tasks_rows,
    )


@router.post("/categories", response_model=OpsTaskCategoryOut)
def create_category(
    payload: OpsTaskCategoryCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_module_access(MODULE, AccessLevel.EDIT)),
):
    staff = _target_user(db, current_user, payload.owner_user_id)
    existing_count = (
        db.query(OpsTaskCategory)
        .filter(OpsTaskCategory.owner_user_id == staff.id)
        .filter(OpsTaskCategory.is_active)
        .count()
    )
    category = OpsTaskCategory(
        company_id=current_user.company_id,
        owner_user_id=staff.id,
        name=payload.name,
        cadence_label=payload.cadence_label,
        sort_order=existing_count,
    )
    db.add(category)
    db.flush()
    audit.record(
        db,
        entity_type="ops_task_category",
        entity_id=category.id,
        action="created",
        actor_user_id=current_user.id,
        details=f"owner={staff.full_name}, name={payload.name}",
    )
    db.commit()
    db.refresh(category)
    return category


def _category_or_404(db: Session, company_id: uuid.UUID, category_id: uuid.UUID) -> OpsTaskCategory:
    category = db.get(OpsTaskCategory, category_id)
    if not category or category.company_id != company_id:
        raise HTTPException(status_code=404, detail="Category not found")
    return category


@router.post("/tasks", response_model=OpsTaskOut)
def create_task(
    payload: OpsTaskCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_module_access(MODULE, AccessLevel.EDIT)),
):
    category = _category_or_404(db, current_user.company_id, payload.category_id)
    # Anyone editing must own the category, or be a manager.
    _target_user(db, current_user, category.owner_user_id)

    task = OpsTask(
        company_id=current_user.company_id,
        category_id=category.id,
        owner_user_id=category.owner_user_id,
        title=payload.title,
        status=payload.status,
        next_action=payload.next_action,
        owner_label=payload.owner_label,
        due_label=payload.due_label,
        follow_up_staff_id=payload.follow_up_staff_id,
        follow_up_date=payload.follow_up_date,
    )
    db.add(task)
    db.flush()
    audit.record(
        db,
        entity_type="ops_task",
        entity_id=task.id,
        action="created",
        actor_user_id=current_user.id,
        details=f"category={category.name}, title={payload.title}",
    )
    db.commit()
    db.refresh(task)
    return _task_out(task, {})


def _task_or_404(db: Session, company_id: uuid.UUID, task_id: uuid.UUID) -> OpsTask:
    task = db.get(OpsTask, task_id)
    if not task or task.company_id != company_id:
        raise HTTPException(status_code=404, detail="Task not found")
    return task


@router.patch("/tasks/{task_id}", response_model=OpsTaskOut)
def update_task(
    task_id: uuid.UUID,
    payload: OpsTaskUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_module_access(MODULE, AccessLevel.EDIT)),
):
    task = _task_or_404(db, current_user.company_id, task_id)
    _target_user(db, current_user, task.owner_user_id)

    old_status = task.status
    fields = payload.model_dump(exclude_unset=True, exclude={"clear_follow_up_staff", "clear_follow_up_date"})
    for field, value in fields.items():
        setattr(task, field, value)
    if payload.clear_follow_up_staff:
        task.follow_up_staff_id = None
    if payload.clear_follow_up_date:
        task.follow_up_date = None

    if payload.status is not None and payload.status != old_status:
        audit.record(
            db,
            entity_type="ops_task",
            entity_id=task.id,
            action="status_changed",
            actor_user_id=current_user.id,
            old_value={"status": old_status.value},
            new_value={"status": task.status.value},
        )
    db.commit()
    db.refresh(task)

    staff_names = {}
    if task.follow_up_staff_id:
        u = db.get(User, task.follow_up_staff_id)
        if u:
            staff_names[u.id] = u.full_name
    return _task_out(task, staff_names)


@router.post("/tasks/{task_id}/archive", response_model=OpsTaskOut)
def archive_task(
    task_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_module_access(MODULE, AccessLevel.EDIT)),
):
    task = _task_or_404(db, current_user.company_id, task_id)
    _target_user(db, current_user, task.owner_user_id)
    task.is_active = False
    audit.record(
        db,
        entity_type="ops_task",
        entity_id=task.id,
        action="archived",
        actor_user_id=current_user.id,
    )
    db.commit()
    db.refresh(task)
    return _task_out(task, {})
