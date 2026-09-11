"""Ops Dashboard: a personal, freeform task tracker per staff member.

Confirmed 2026-09-11 ("Create a staff individual ops dashboard based on
the staff login"), modeled on a sample screenshot showing categories of
tasks (e.g. "Comms & calendar", "Finance / Odoo") each with a status,
next action, owner, due label, and a follow-up staff/date handoff.

Confirmed scope (2026-09-11): this sits ALONGSIDE real ERP data, not
instead of it -- a category/task here is manually created and edited,
independent of Job Orders/Software Tasks/Contracts. The dashboard also
shows a separate read-only rollup of the viewer's actual assigned Job
Orders and Software Tasks (see app/routers/ops_dashboard.py) -- that
rollup needs no new model, since it's just filtered reads of existing
tables.

Visibility (confirmed 2026-09-11): each staff member's dashboard shows
only their own categories/tasks (owner_user_id = them) by default;
Owner/Service Lead/Sales Manager can also view and edit another staff
member's dashboard for oversight -- see MANAGER_ROLES in
app/routers/ops_dashboard.py.
"""
import enum
import uuid
from datetime import date, datetime

from sqlalchemy import Boolean, Date, DateTime, Enum, ForeignKey, Integer, String, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base


class OpsTaskStatus(str, enum.Enum):
    NOT_STARTED = "not_started"
    IN_PROGRESS = "in_progress"
    WATCH = "watch"
    BLOCKED = "blocked"
    DONE = "done"


class OpsTaskCategory(Base):
    """A section on one staff member's dashboard (e.g. "Comms &
    calendar"). Scoped to a single owner, not shared/company-wide --
    each staff member's dashboard is their own."""

    __tablename__ = "ops_task_categories"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    company_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("companies.id"), nullable=False)
    owner_user_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id"), nullable=False)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    # Free text cadence note shown under the category name in the
    # sample (e.g. "Weekly / month-end") -- a label, not a scheduling
    # rule the system enforces.
    cadence_label: Mapped[str | None] = mapped_column(String(255), nullable=True)
    sort_order: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    tasks: Mapped[list["OpsTask"]] = relationship(back_populates="category")


class OpsTask(Base):
    __tablename__ = "ops_tasks"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    company_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("companies.id"), nullable=False)
    category_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("ops_task_categories.id"), nullable=False)
    # Denormalized from the category for simpler permission checks and
    # filtering -- always equal to category.owner_user_id.
    owner_user_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id"), nullable=False)

    title: Mapped[str] = mapped_column(String(500), nullable=False)
    status: Mapped[OpsTaskStatus] = mapped_column(
        Enum(OpsTaskStatus, name="ops_task_status"), default=OpsTaskStatus.NOT_STARTED, nullable=False
    )
    next_action: Mapped[str | None] = mapped_column(String(500), nullable=True)
    # Free text, not a User FK -- the sample shows values like "Dennis +
    # Bot" alongside plain staff names, not always one real account.
    owner_label: Mapped[str | None] = mapped_column(String(255), nullable=True)
    # Free text -- the sample mixes real dates with cadence labels like
    # "Month-end" in the same column.
    due_label: Mapped[str | None] = mapped_column(String(100), nullable=True)
    follow_up_staff_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("users.id"), nullable=True)
    follow_up_date: Mapped[date | None] = mapped_column(Date, nullable=True)

    # Seeded demo rows are flagged so they're visually distinguishable
    # ("(sample)" suffix in the UI) -- there is no in-app "reset seed"
    # action (see module docstring / open-business-decisions.md): real
    # task data should never be silently wiped by a button click.
    is_sample: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    # Soft-delete, matching every other master record in this system.
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    category: Mapped["OpsTaskCategory"] = relationship(back_populates="tasks")
