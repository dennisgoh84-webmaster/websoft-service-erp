"""
Seed a clean demo dataset for the Websoft Service ERP Solution
Service Operations core slice.

Run with: uv run python scripts/seed_demo.py

Sets up:
- Company: Webmaster Consultancy Pte Ltd
- Module catalog + per-company module enablement (Module Control /
  licensing) -- Service Operations core modules enabled, everything
  else (including Commission Management and Integrations/Odoo
  migration, deferred for now) left disabled.
- Users: Dennis (owner), Nico (service_lead), Cherish (sales_manager),
  Wei Ling (support_engineer) -- all password "demo1234"
- Customer: Acme Manufacturing Pte Ltd
- One Active 10-hour contract (SGD 3,000), already invoiced annually
- A job order with Service Records already approved, deliberately left
  just short of exhausting the contract, PLUS one final SUBMITTED
  (not yet approved) record that will push it into Excess Usage --
  left pending on purpose so a live walkthrough can approve it and
  perform the Nico excess-usage review itself, rather than the seed
  script doing it upfront.
"""
import sys
from datetime import date, datetime, timedelta, timezone
from pathlib import Path

sys.path.append(str(Path(__file__).resolve().parents[1]))

from sqlalchemy import text

from app.core.database import Base, SessionLocal, engine
from app.models.core import Company, User, UserRole
from app.models.customers import Customer
from app.models.job_orders import JobOrder, JobOrderPriority, JobOrderStatus
from app.models.licensing import CompanyModule, LicenseType, Module
from app.services import billing as billing_svc
from app.services import contracts as contract_svc
from app.services import service_records as sr_svc
from app.services.auth import hash_password

DEMO_PASSWORD = "demo1234"

# key -> (name, description, is_built, enabled_by_default)
# Matches the 19 modules in docs/module-map.md. Commission Management
# and Integrations (which owns future Odoo migration work) are listed
# for completeness of the control plane but left disabled/not built --
# deferred at the user's request until Service Operations is finalized.
MODULE_CATALOG = [
    ("core_administration", "Core / Administration", True, True),
    ("crm", "CRM", False, False),
    ("sales", "Sales", False, False),
    ("customer_management", "Customer Management", True, True),
    ("service_contracts", "Service Contracts", True, True),
    ("service_operations", "Helpdesk / Service Operations (Job Orders)", True, True),
    ("projects", "Projects", False, False),
    ("service_records", "Service Records", True, True),
    ("billing", "Billing", True, True),
    ("accounts_receivable", "Accounts Receivable", False, False),
    ("accounts_payable", "Accounts Payable", False, False),
    ("purchasing", "Purchasing", False, False),
    ("inventory", "Inventory", False, False),
    ("hardware_management", "Hardware Management", False, False),
    ("commission_management", "Commission Management", False, False),  # deferred
    ("finance_accounting", "Finance / Accounting", False, False),
    ("reporting", "Reporting / Management Dashboard", True, True),
    ("integrations", "Integrations (incl. Odoo migration)", False, False),  # deferred
    ("ai_assistant", "AI Assistant", False, False),
]


def wipe_data(db):
    """Truncate all app tables for a clean, repeatable demo reset."""
    table_names = [t.name for t in reversed(Base.metadata.sorted_tables)]
    if table_names:
        db.execute(text(f"TRUNCATE TABLE {', '.join(table_names)} RESTART IDENTITY CASCADE"))
    db.commit()


def seed_modules(db, company: Company):
    for key, name, is_built, enabled in MODULE_CATALOG:
        db.add(Module(key=key, name=name, is_built=is_built))
        db.add(
            CompanyModule(
                company_id=company.id,
                module_key=key,
                enabled=enabled,
                license_type=LicenseType.INCLUDED,
                enabled_at=datetime.now(timezone.utc) if enabled else None,
            )
        )
    db.flush()


def main():
    Base.metadata.create_all(bind=engine)  # no-op if migrations already applied
    db = SessionLocal()
    try:
        wipe_data(db)

        company = Company(name="Webmaster Consultancy Pte Ltd")
        db.add(company)
        db.flush()

        seed_modules(db, company)

        dennis = User(
            company_id=company.id, email="dennis@websoft.local",
            hashed_password=hash_password(DEMO_PASSWORD), full_name="Dennis (Owner)",
            role=UserRole.OWNER,
        )
        nico = User(
            company_id=company.id, email="nico@websoft.local",
            hashed_password=hash_password(DEMO_PASSWORD), full_name="Nico (Service & Support Lead)",
            role=UserRole.SERVICE_LEAD,
        )
        cherish = User(
            company_id=company.id, email="cherish@websoft.local",
            hashed_password=hash_password(DEMO_PASSWORD), full_name="Cherish (Sales Manager)",
            role=UserRole.SALES_MANAGER,
        )
        engineer = User(
            company_id=company.id, email="weiling@websoft.local",
            hashed_password=hash_password(DEMO_PASSWORD), full_name="Wei Ling (Support Engineer)",
            role=UserRole.SUPPORT_ENGINEER,
        )
        db.add_all([dennis, nico, cherish, engineer])
        db.flush()

        customer = Customer(
            company_id=company.id, name="Acme Manufacturing Pte Ltd",
            billing_email="accounts@acme-mfg.test",
        )
        db.add(customer)
        db.flush()

        contract = contract_svc.create_contract(
            db, company_id=company.id, customer_id=customer.id,
            contracted_hours=10, contract_value_sgd=3000,
            start_date=date.today() - timedelta(days=60),
            actor_user_id=dennis.id,
        )
        contract_svc.activate_contract(db, contract, actor_user_id=dennis.id)
        billing_svc.issue_contract_annual_invoice(db, contract, actor_user_id=dennis.id)

        job_order = JobOrder(
            customer_id=customer.id, contract_id=contract.id,
            subject="Intermittent VPN connectivity for remote staff",
            priority=JobOrderPriority.HIGH, status=JobOrderStatus.ASSIGNED,
            assigned_to_user_id=engineer.id,
        )
        db.add(job_order)
        db.flush()

        # Already-approved work totalling 540 of the 600 contracted minutes.
        for i, raw_minutes in enumerate([240, 300]):
            record = sr_svc.submit_service_record(
                db, job_order_id=job_order.id, employee_user_id=engineer.id,
                work_date=date.today() - timedelta(days=10 - i * 3), raw_minutes=raw_minutes,
            )
            sr_svc.approve_service_record(db, record, job_order, approver=nico)

        db.commit()
        print(f"Consumed so far: {contract.consumed_minutes} / {contract.contracted_minutes} minutes")

        # Final record left SUBMITTED (not approved) on purpose -- 80 raw
        # minutes rounds to 90 (SRV-007), only 60 remain, so approving this
        # live in the demo will exhaust the contract AND create an Excess
        # Usage record of 30 minutes for Nico to review on camera.
        final_record = sr_svc.submit_service_record(
            db, job_order_id=job_order.id, employee_user_id=engineer.id,
            work_date=date.today(), raw_minutes=80,
        )
        db.commit()

        print("\n=== Demo dataset ready ===")
        print(f"Company:  {company.name}")
        print(f"Customer: {customer.name} ({customer.id})")
        print(f"Contract: {contract.id} -- {contract.consumed_minutes}/{contract.contracted_minutes} min consumed")
        print(f"Job order: {job_order.id} -- {job_order.subject}")
        print(f"Pending service record (approve live in demo): {final_record.id} -- {final_record.raw_minutes} raw min -> {final_record.rounded_minutes} rounded min")
        print("\nEnabled modules:", ", ".join(k for k, _, _, e in MODULE_CATALOG if e))
        print("\nLogins (all password: demo1234):")
        for u in (dennis, nico, cherish, engineer):
            print(f"  {u.email:30s} {u.role.value}")
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()


if __name__ == "__main__":
    main()
