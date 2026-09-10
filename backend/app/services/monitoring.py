"""Support monitoring: per-staff Job Order workload and contract-hours
throughput, so a supervisor can see who's overloaded at a glance.
Confirmed 2026-09-10 (reference: a legacy "Monitoring Support" screen).

Open items, deliberately not guessed:
  - "Due soon" has no confirmed lead time -- DUE_SOON_LEAD_DAYS below is
    a pragmatic default (2 days), not a confirmed business rule.

"Un-Test S/T" is Software Task rows (app/models/software_tasks.py)
assigned to a staff member for testing but not yet marked tested --
counted per tester below.
"""
import uuid
from dataclasses import dataclass, field
from datetime import date

from sqlalchemy.orm import Session

from app.models.core import User, UserRole
from app.models.job_orders import JobOrder, JobOrderStatus
from app.models.service_records import ServiceRecord, ServiceRecordOutcome, ServiceRecordStatus
from app.models.software_tasks import SoftwareTask

# Pragmatic default, not a confirmed SLA rule (SRV-009 remains deferred)
# -- only used to bucket a Job Order that already has a manually-set
# due_date into "due soon" vs. merely "overdue" vs. neither.
DUE_SOON_LEAD_DAYS = 2

OPEN_STATUSES = (JobOrderStatus.OPEN, JobOrderStatus.ASSIGNED)


@dataclass
class StaffMonitoring:
    user_id: uuid.UUID
    full_name: str
    open_job_orders: int = 0
    overdue_job_orders: int = 0
    due_soon_job_orders: int = 0
    pending_service_records: int = 0
    untested_software_tasks: int = 0
    cm_svc_records_month: int = 0
    cm_svc_records_today: int = 0
    cm_svc_hours_month: float = 0.0
    cm_svc_hours_today: float = 0.0
    avg_daily_contract_hours: float = 0.0


@dataclass
class MonitoringSummary:
    total_job_orders: int = 0
    total_open_job_orders: int = 0
    total_overdue_job_orders: int = 0
    unassigned_job_orders: int = 0
    total_pending_service_records: int = 0
    total_untested_software_tasks: int = 0


@dataclass
class SupportMonitoring:
    as_at: date
    summary: MonitoringSummary
    staff: list[StaffMonitoring] = field(default_factory=list)
    unassigned: StaffMonitoring | None = None


def get_support_monitoring(db: Session, *, company_id: uuid.UUID, as_of: date | None = None) -> SupportMonitoring:
    as_of = as_of or date.today()
    month_start = as_of.replace(day=1)

    job_orders = db.query(JobOrder).filter(JobOrder.company_id == company_id).all()
    service_records = (
        db.query(ServiceRecord)
        .join(JobOrder, ServiceRecord.job_order_id == JobOrder.id)
        .filter(JobOrder.company_id == company_id)
        .all()
    )
    untested_tasks = (
        db.query(SoftwareTask)
        .filter(SoftwareTask.company_id == company_id, ~SoftwareTask.is_tested)
        .all()
    )
    staff = (
        db.query(User)
        .filter(User.company_id == company_id, User.is_active, User.role != UserRole.OWNER)
        .order_by(User.full_name)
        .all()
    )

    by_staff: dict[uuid.UUID, StaffMonitoring] = {
        u.id: StaffMonitoring(user_id=u.id, full_name=u.full_name) for u in staff
    }
    unassigned = StaffMonitoring(user_id=uuid.UUID(int=0), full_name="Un-Assigned")

    summary = MonitoringSummary()

    for jo in job_orders:
        summary.total_job_orders += 1
        is_open = jo.status in OPEN_STATUSES
        if is_open:
            summary.total_open_job_orders += 1

        row = by_staff.get(jo.assigned_to_user_id) if jo.assigned_to_user_id else None
        if row is None and jo.assigned_to_user_id is None:
            row = unassigned
            if is_open:
                summary.unassigned_job_orders += 1

        if row is not None and is_open:
            row.open_job_orders += 1
            if jo.due_date is not None:
                days_left = (jo.due_date - as_of).days
                if days_left < 0:
                    row.overdue_job_orders += 1
                    summary.total_overdue_job_orders += 1
                elif days_left <= DUE_SOON_LEAD_DAYS:
                    row.due_soon_job_orders += 1

    for sr in service_records:
        row = by_staff.get(sr.employee_user_id)
        if row is None:
            continue
        if sr.status == ServiceRecordStatus.SUBMITTED:
            row.pending_service_records += 1
            summary.total_pending_service_records += 1
        if sr.status != ServiceRecordStatus.APPROVED or sr.approved_at is None:
            continue
        approved_date = sr.approved_at.date()
        if approved_date < month_start:
            continue
        row.cm_svc_records_month += 1
        if approved_date == as_of:
            row.cm_svc_records_today += 1
        if sr.outcome == ServiceRecordOutcome.CONTRACT_DEDUCTION:
            hours = sr.rounded_minutes / 60
            row.cm_svc_hours_month += hours
            if approved_date == as_of:
                row.cm_svc_hours_today += hours

    for task in untested_tasks:
        row = by_staff.get(task.tester_user_id) if task.tester_user_id else None
        if row is not None:
            row.untested_software_tasks += 1
        summary.total_untested_software_tasks += 1

    # Average daily contract hours deducted this month, per staff --
    # denominator is the number of distinct days *so far this month*
    # (not distinct days worked), so it reads as "how many hours a day
    # is this person contributing on average" rather than being
    # inflated by only counting days they happened to log something.
    days_elapsed_this_month = (as_of - month_start).days + 1
    for row in by_staff.values():
        if days_elapsed_this_month > 0:
            row.avg_daily_contract_hours = row.cm_svc_hours_month / days_elapsed_this_month

    return SupportMonitoring(
        as_at=as_of, summary=summary, staff=list(by_staff.values()), unassigned=unassigned
    )
