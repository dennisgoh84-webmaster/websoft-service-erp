"""
Operations Reports and Accounting Reports -- filterable, exportable
views over data other modules already own and compute (contracts, job
orders, service records, AR/AP aging, the GL trial balance). No new
business rule is introduced here; see app/services/reports.py.

Kept as two module_keys rather than reusing "reporting" (Support
Monitoring's module) so Group Authority can grant them independently --
e.g. Finance Team gets accounting_reports without also getting Support
Monitoring, and Service/Sales get operations_reports without accounting
detail. Every list endpoint doubles as a CSV/Excel export (literal
`/export.csv` and `/export.xlsx` paths registered before any `/{id}`-
style route, per the pattern in app/routers/billing.py), and every
export is written to the audit trail (app/services/audit.py) since it
is data leaving the system as a file, unlike a screen view.
"""
import uuid
from datetime import date

from fastapi import APIRouter, Depends
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.models.contracts import ContractKind, ContractStatus
from app.models.core import User
from app.models.customers import Customer
from app.models.groups import AccessLevel
from app.models.job_orders import JobOrderStatus
from app.models.service_records import ServiceRecordOutcome, ServiceRecordStatus
from app.schemas.schemas import (
    AgingReport,
    APAgingReport,
    APAgingRow,
    AgingRow,
    ContractOut,
    JobOrderOut,
    ServiceRecordOut,
    TrialBalance,
    TrialBalanceRow,
)
from app.services import audit
from app.services import exports
from app.services import ledger as ledger_svc
from app.services import reports as reports_svc
from app.services.authority import require_module_access

router = APIRouter(prefix="/api/reports", tags=["reports"])
OPS_MODULE = "operations_reports"
ACCOUNTING_MODULE = "accounting_reports"


def _audit_export(db: Session, current_user: User, report_name: str, fmt: str, row_count: int) -> None:
    audit.record(
        db,
        entity_type="report",
        entity_id=current_user.id,
        action="export",
        actor_user_id=current_user.id,
        details=f"{report_name} exported as {fmt.upper()} ({row_count} row{'s' if row_count != 1 else ''})",
    )
    db.commit()


def _customer_names(db: Session, company_id: uuid.UUID) -> dict:
    return {c.id: c.name for c in db.query(Customer).filter(Customer.company_id == company_id)}


def _user_names(db: Session, company_id: uuid.UUID) -> dict:
    # Staff belong to a company via UserCompanyAccess; a simple id->name
    # map for whichever users appear in the result set is all a report
    # needs, so this just loads everyone and looks up on demand.
    from app.models.core import User as UserModel

    return {u.id: u.full_name for u in db.query(UserModel).all()}


# ==== Operations Reports ================================================


@router.get("/operations/contracts", response_model=list[ContractOut])
def contracts_report(
    status: ContractStatus | None = None,
    contract_kind: ContractKind | None = None,
    customer_id: uuid.UUID | None = None,
    expiring_within_days: int | None = None,
    start_date: date | None = None,
    end_date: date | None = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_module_access(OPS_MODULE, AccessLevel.VIEW)),
):
    contracts = reports_svc.list_contracts_report(
        db,
        current_user.company_id,
        status=status,
        contract_kind=contract_kind,
        customer_id=customer_id,
        expiring_within_days=expiring_within_days,
        start_date=start_date,
        end_date=end_date,
    )
    return [ContractOut.from_model(c) for c in contracts]


def _contract_export_rows(db: Session, current_user: User, **filters) -> list[dict]:
    contracts = reports_svc.list_contracts_report(db, current_user.company_id, **filters)
    names = _customer_names(db, current_user.company_id)
    return [
        {
            "customer_name": names.get(c.customer_id, ""),
            "status": c.status.value,
            "contract_kind": c.contract_kind.value,
            "contracted_hours": f"{c.contracted_minutes / 60:.2f}",
            "consumed_hours": f"{c.consumed_minutes / 60:.2f}",
            "remaining_hours": f"{c.remaining_minutes / 60:.2f}",
            "contract_value_sgd": f"{c.contract_value_sgd:.2f}",
            "start_date": c.start_date.isoformat(),
            "end_date": c.end_date.isoformat(),
        }
        for c in contracts
    ]


CONTRACT_EXPORT_FIELDS = [
    "customer_name", "status", "contract_kind", "contracted_hours", "consumed_hours",
    "remaining_hours", "contract_value_sgd", "start_date", "end_date",
]


@router.get("/operations/contracts/export.csv")
def contracts_report_export_csv(
    status: ContractStatus | None = None,
    contract_kind: ContractKind | None = None,
    customer_id: uuid.UUID | None = None,
    expiring_within_days: int | None = None,
    start_date: date | None = None,
    end_date: date | None = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_module_access(OPS_MODULE, AccessLevel.VIEW)),
):
    rows = _contract_export_rows(
        db, current_user, status=status, contract_kind=contract_kind, customer_id=customer_id,
        expiring_within_days=expiring_within_days, start_date=start_date, end_date=end_date,
    )
    _audit_export(db, current_user, "Operations Report: Contracts", "csv", len(rows))
    csv_text = exports.rows_to_csv(CONTRACT_EXPORT_FIELDS, rows)
    return StreamingResponse(
        iter([csv_text]),
        media_type="text/csv",
        headers={"Content-Disposition": "attachment; filename=contracts-report.csv"},
    )


@router.get("/operations/contracts/export.xlsx")
def contracts_report_export_excel(
    status: ContractStatus | None = None,
    contract_kind: ContractKind | None = None,
    customer_id: uuid.UUID | None = None,
    expiring_within_days: int | None = None,
    start_date: date | None = None,
    end_date: date | None = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_module_access(OPS_MODULE, AccessLevel.VIEW)),
):
    rows = _contract_export_rows(
        db, current_user, status=status, contract_kind=contract_kind, customer_id=customer_id,
        expiring_within_days=expiring_within_days, start_date=start_date, end_date=end_date,
    )
    _audit_export(db, current_user, "Operations Report: Contracts", "excel", len(rows))
    data = exports.rows_to_excel(CONTRACT_EXPORT_FIELDS, rows, sheet_name="Contracts")
    return StreamingResponse(
        iter([data]),
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": "attachment; filename=contracts-report.xlsx"},
    )


@router.get("/operations/job-orders", response_model=list[JobOrderOut])
def job_orders_report(
    status: JobOrderStatus | None = None,
    customer_id: uuid.UUID | None = None,
    assigned_to_user_id: uuid.UUID | None = None,
    overdue_only: bool = False,
    start_date: date | None = None,
    end_date: date | None = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_module_access(OPS_MODULE, AccessLevel.VIEW)),
):
    return reports_svc.list_job_orders_report(
        db,
        current_user.company_id,
        status=status,
        customer_id=customer_id,
        assigned_to_user_id=assigned_to_user_id,
        overdue_only=overdue_only,
        start_date=start_date,
        end_date=end_date,
    )


def _job_order_export_rows(db: Session, current_user: User, **filters) -> list[dict]:
    orders = reports_svc.list_job_orders_report(db, current_user.company_id, **filters)
    customer_names = _customer_names(db, current_user.company_id)
    user_names = _user_names(db, current_user.company_id)
    today = date.today()
    return [
        {
            "customer_name": customer_names.get(o.customer_id, ""),
            "subject": o.subject,
            "priority": o.priority.value,
            "status": o.status.value,
            "assigned_to": user_names.get(o.assigned_to_user_id, "") if o.assigned_to_user_id else "",
            "due_date": o.due_date.isoformat() if o.due_date else "",
            "overdue": "Yes" if (o.due_date and o.due_date < today and o.status.value not in ("resolved", "closed")) else "No",
            "created_at": o.created_at.date().isoformat(),
        }
        for o in orders
    ]


JOB_ORDER_EXPORT_FIELDS = [
    "customer_name", "subject", "priority", "status", "assigned_to", "due_date", "overdue", "created_at",
]


@router.get("/operations/job-orders/export.csv")
def job_orders_report_export_csv(
    status: JobOrderStatus | None = None,
    customer_id: uuid.UUID | None = None,
    assigned_to_user_id: uuid.UUID | None = None,
    overdue_only: bool = False,
    start_date: date | None = None,
    end_date: date | None = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_module_access(OPS_MODULE, AccessLevel.VIEW)),
):
    rows = _job_order_export_rows(
        db, current_user, status=status, customer_id=customer_id, assigned_to_user_id=assigned_to_user_id,
        overdue_only=overdue_only, start_date=start_date, end_date=end_date,
    )
    _audit_export(db, current_user, "Operations Report: Job Orders", "csv", len(rows))
    csv_text = exports.rows_to_csv(JOB_ORDER_EXPORT_FIELDS, rows)
    return StreamingResponse(
        iter([csv_text]),
        media_type="text/csv",
        headers={"Content-Disposition": "attachment; filename=job-orders-report.csv"},
    )


@router.get("/operations/job-orders/export.xlsx")
def job_orders_report_export_excel(
    status: JobOrderStatus | None = None,
    customer_id: uuid.UUID | None = None,
    assigned_to_user_id: uuid.UUID | None = None,
    overdue_only: bool = False,
    start_date: date | None = None,
    end_date: date | None = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_module_access(OPS_MODULE, AccessLevel.VIEW)),
):
    rows = _job_order_export_rows(
        db, current_user, status=status, customer_id=customer_id, assigned_to_user_id=assigned_to_user_id,
        overdue_only=overdue_only, start_date=start_date, end_date=end_date,
    )
    _audit_export(db, current_user, "Operations Report: Job Orders", "excel", len(rows))
    data = exports.rows_to_excel(JOB_ORDER_EXPORT_FIELDS, rows, sheet_name="Job Orders")
    return StreamingResponse(
        iter([data]),
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": "attachment; filename=job-orders-report.xlsx"},
    )


@router.get("/operations/service-records", response_model=list[ServiceRecordOut])
def service_records_report(
    status: ServiceRecordStatus | None = None,
    outcome: ServiceRecordOutcome | None = None,
    customer_id: uuid.UUID | None = None,
    employee_user_id: uuid.UUID | None = None,
    start_date: date | None = None,
    end_date: date | None = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_module_access(OPS_MODULE, AccessLevel.VIEW)),
):
    return reports_svc.list_service_records_report(
        db,
        current_user.company_id,
        status=status,
        outcome=outcome,
        customer_id=customer_id,
        employee_user_id=employee_user_id,
        start_date=start_date,
        end_date=end_date,
    )


def _service_record_export_rows(db: Session, current_user: User, **filters) -> list[dict]:
    records = reports_svc.list_service_records_report(db, current_user.company_id, **filters)
    user_names = _user_names(db, current_user.company_id)
    from app.models.job_orders import JobOrder

    job_order_customers = {
        jo.id: jo.customer_id
        for jo in db.query(JobOrder).filter(JobOrder.company_id == current_user.company_id)
    }
    customer_names = _customer_names(db, current_user.company_id)
    return [
        {
            "work_date": r.work_date.isoformat(),
            "customer_name": customer_names.get(job_order_customers.get(r.job_order_id), ""),
            "employee": user_names.get(r.employee_user_id, ""),
            "hours": f"{r.rounded_minutes / 60:.2f}",
            "status": r.status.value,
            "outcome": r.outcome.value,
            "is_late": "Yes" if r.is_late else "No",
        }
        for r in records
    ]


SERVICE_RECORD_EXPORT_FIELDS = ["work_date", "customer_name", "employee", "hours", "status", "outcome", "is_late"]


@router.get("/operations/service-records/export.csv")
def service_records_report_export_csv(
    status: ServiceRecordStatus | None = None,
    outcome: ServiceRecordOutcome | None = None,
    customer_id: uuid.UUID | None = None,
    employee_user_id: uuid.UUID | None = None,
    start_date: date | None = None,
    end_date: date | None = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_module_access(OPS_MODULE, AccessLevel.VIEW)),
):
    rows = _service_record_export_rows(
        db, current_user, status=status, outcome=outcome, customer_id=customer_id,
        employee_user_id=employee_user_id, start_date=start_date, end_date=end_date,
    )
    _audit_export(db, current_user, "Operations Report: Service Records", "csv", len(rows))
    csv_text = exports.rows_to_csv(SERVICE_RECORD_EXPORT_FIELDS, rows)
    return StreamingResponse(
        iter([csv_text]),
        media_type="text/csv",
        headers={"Content-Disposition": "attachment; filename=service-records-report.csv"},
    )


@router.get("/operations/service-records/export.xlsx")
def service_records_report_export_excel(
    status: ServiceRecordStatus | None = None,
    outcome: ServiceRecordOutcome | None = None,
    customer_id: uuid.UUID | None = None,
    employee_user_id: uuid.UUID | None = None,
    start_date: date | None = None,
    end_date: date | None = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_module_access(OPS_MODULE, AccessLevel.VIEW)),
):
    rows = _service_record_export_rows(
        db, current_user, status=status, outcome=outcome, customer_id=customer_id,
        employee_user_id=employee_user_id, start_date=start_date, end_date=end_date,
    )
    _audit_export(db, current_user, "Operations Report: Service Records", "excel", len(rows))
    data = exports.rows_to_excel(SERVICE_RECORD_EXPORT_FIELDS, rows, sheet_name="Service Records")
    return StreamingResponse(
        iter([data]),
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": "attachment; filename=service-records-report.xlsx"},
    )


# ==== Accounting Reports =================================================


def _ar_aging_report(db: Session, company_id: uuid.UUID, as_at: date | None) -> AgingReport:
    as_at = as_at or date.today()
    rows = [
        AgingRow(
            customer_id=r["customer_id"],
            customer_name=r["customer_name"],
            current=float(r["current"]),
            days_1_30=float(r["days_1_30"]),
            days_31_60=float(r["days_31_60"]),
            days_61_90=float(r["days_61_90"]),
            over_90=float(r["over_90"]),
            total=float(r["total"]),
        )
        for r in reports_svc.ar_aging_rows(db, company_id, as_at)
    ]
    return AgingReport(
        as_at=as_at,
        rows=rows,
        current=sum(r.current for r in rows),
        days_1_30=sum(r.days_1_30 for r in rows),
        days_31_60=sum(r.days_31_60 for r in rows),
        days_61_90=sum(r.days_61_90 for r in rows),
        over_90=sum(r.over_90 for r in rows),
        total=sum(r.total for r in rows),
    )


def _ap_aging_report(db: Session, company_id: uuid.UUID, as_at: date | None) -> APAgingReport:
    as_at = as_at or date.today()
    rows = [
        APAgingRow(
            supplier_id=r["supplier_id"],
            supplier_name=r["supplier_name"],
            current=float(r["current"]),
            days_1_30=float(r["days_1_30"]),
            days_31_60=float(r["days_31_60"]),
            days_61_90=float(r["days_61_90"]),
            over_90=float(r["over_90"]),
            total=float(r["total"]),
        )
        for r in reports_svc.ap_aging_rows(db, company_id, as_at)
    ]
    return APAgingReport(as_at=as_at, rows=rows, total=sum(r.total for r in rows))


@router.get("/accounting/ar-aging", response_model=AgingReport)
def ar_aging_report(
    as_at: date | None = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_module_access(ACCOUNTING_MODULE, AccessLevel.VIEW)),
):
    return _ar_aging_report(db, current_user.company_id, as_at)


@router.get("/accounting/ar-aging/export.csv")
def ar_aging_report_export_csv(
    as_at: date | None = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_module_access(ACCOUNTING_MODULE, AccessLevel.VIEW)),
):
    report = _ar_aging_report(db, current_user.company_id, as_at)
    fields = ["customer_name", "current", "days_1_30", "days_31_60", "days_61_90", "over_90", "total"]
    rows = [r.model_dump() for r in report.rows]
    _audit_export(db, current_user, "Accounting Report: AR Aging", "csv", len(rows))
    csv_text = exports.rows_to_csv(fields, rows)
    return StreamingResponse(
        iter([csv_text]), media_type="text/csv",
        headers={"Content-Disposition": "attachment; filename=ar-aging-report.csv"},
    )


@router.get("/accounting/ar-aging/export.xlsx")
def ar_aging_report_export_excel(
    as_at: date | None = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_module_access(ACCOUNTING_MODULE, AccessLevel.VIEW)),
):
    report = _ar_aging_report(db, current_user.company_id, as_at)
    fields = ["customer_name", "current", "days_1_30", "days_31_60", "days_61_90", "over_90", "total"]
    rows = [r.model_dump() for r in report.rows]
    _audit_export(db, current_user, "Accounting Report: AR Aging", "excel", len(rows))
    data = exports.rows_to_excel(fields, rows, sheet_name="AR Aging")
    return StreamingResponse(
        iter([data]), media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": "attachment; filename=ar-aging-report.xlsx"},
    )


@router.get("/accounting/ap-aging", response_model=APAgingReport)
def ap_aging_report(
    as_at: date | None = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_module_access(ACCOUNTING_MODULE, AccessLevel.VIEW)),
):
    return _ap_aging_report(db, current_user.company_id, as_at)


@router.get("/accounting/ap-aging/export.csv")
def ap_aging_report_export_csv(
    as_at: date | None = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_module_access(ACCOUNTING_MODULE, AccessLevel.VIEW)),
):
    report = _ap_aging_report(db, current_user.company_id, as_at)
    fields = ["supplier_name", "current", "days_1_30", "days_31_60", "days_61_90", "over_90", "total"]
    rows = [r.model_dump() for r in report.rows]
    _audit_export(db, current_user, "Accounting Report: AP Aging", "csv", len(rows))
    csv_text = exports.rows_to_csv(fields, rows)
    return StreamingResponse(
        iter([csv_text]), media_type="text/csv",
        headers={"Content-Disposition": "attachment; filename=ap-aging-report.csv"},
    )


@router.get("/accounting/ap-aging/export.xlsx")
def ap_aging_report_export_excel(
    as_at: date | None = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_module_access(ACCOUNTING_MODULE, AccessLevel.VIEW)),
):
    report = _ap_aging_report(db, current_user.company_id, as_at)
    fields = ["supplier_name", "current", "days_1_30", "days_31_60", "days_61_90", "over_90", "total"]
    rows = [r.model_dump() for r in report.rows]
    _audit_export(db, current_user, "Accounting Report: AP Aging", "excel", len(rows))
    data = exports.rows_to_excel(fields, rows, sheet_name="AP Aging")
    return StreamingResponse(
        iter([data]), media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": "attachment; filename=ap-aging-report.xlsx"},
    )


def _trial_balance_report(db: Session, company_id: uuid.UUID, as_at: date | None) -> TrialBalance:
    rows = ledger_svc.account_balances(db, company_id, as_at)
    out = [
        TrialBalanceRow(
            account_id=r["account_id"], code=r["code"], name=r["name"], account_type=r["account_type"],
            debit_sgd=float(r["debit_sgd"]), credit_sgd=float(r["credit_sgd"]), balance_sgd=float(r["balance_sgd"]),
        )
        for r in rows
    ]
    total_debit = sum(r.debit_sgd for r in out)
    total_credit = sum(r.credit_sgd for r in out)
    return TrialBalance(
        as_at=as_at, rows=out, total_debit=total_debit, total_credit=total_credit,
        is_balanced=round(total_debit, 2) == round(total_credit, 2),
    )


@router.get("/accounting/trial-balance", response_model=TrialBalance)
def trial_balance_report(
    as_at: date | None = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_module_access(ACCOUNTING_MODULE, AccessLevel.VIEW)),
):
    return _trial_balance_report(db, current_user.company_id, as_at)


@router.get("/accounting/trial-balance/export.csv")
def trial_balance_report_export_csv(
    as_at: date | None = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_module_access(ACCOUNTING_MODULE, AccessLevel.VIEW)),
):
    report = _trial_balance_report(db, current_user.company_id, as_at)
    fields = ["code", "name", "account_type", "debit_sgd", "credit_sgd", "balance_sgd"]
    rows = [r.model_dump() for r in report.rows]
    _audit_export(db, current_user, "Accounting Report: Trial Balance", "csv", len(rows))
    csv_text = exports.rows_to_csv(fields, rows)
    return StreamingResponse(
        iter([csv_text]), media_type="text/csv",
        headers={"Content-Disposition": "attachment; filename=trial-balance-report.csv"},
    )


@router.get("/accounting/trial-balance/export.xlsx")
def trial_balance_report_export_excel(
    as_at: date | None = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_module_access(ACCOUNTING_MODULE, AccessLevel.VIEW)),
):
    report = _trial_balance_report(db, current_user.company_id, as_at)
    fields = ["code", "name", "account_type", "debit_sgd", "credit_sgd", "balance_sgd"]
    rows = [r.model_dump() for r in report.rows]
    _audit_export(db, current_user, "Accounting Report: Trial Balance", "excel", len(rows))
    data = exports.rows_to_excel(fields, rows, sheet_name="Trial Balance")
    return StreamingResponse(
        iter([data]), media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": "attachment; filename=trial-balance-report.xlsx"},
    )
