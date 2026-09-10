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
- Group Authority: default Groups (Owner / Admin, Service Team, Sales
  Team, Finance Team) with a per-module access matrix, and each seeded
  user assigned to the appropriate Group. Dennis's OWNER role already
  grants him FULL access everywhere regardless of group (see
  app/services/authority.py); he is still put in "Owner / Admin" so
  Staff Master doesn't show him as ungrouped. Nico and Wei Ling both
  land in "Service Team" -- the group grants them broad Service
  Operations/Contracts access, but the SRV-004/SRV-011 named-person
  rule (Nico, or Cherish as backup, decides excess usage) is enforced
  separately by role, not by group, so Wei Ling still can't approve a
  Service Record or decide excess usage despite sharing Nico's group.
- Customer: Acme Manufacturing Pte Ltd
- One Active 10-hour contract (SGD 3,000), already invoiced annually
- A job order with Service Records already approved, deliberately left
  just short of exhausting the contract, PLUS one final SUBMITTED
  (not yet approved) record that will push it into Excess Usage --
  left pending on purpose so a live walkthrough can approve it and
  perform the Nico excess-usage review itself, rather than the seed
  script doing it upfront.
"""
import base64
import sys
from datetime import date, datetime, timedelta, timezone
from decimal import Decimal
from pathlib import Path

sys.path.append(str(Path(__file__).resolve().parents[1]))

from sqlalchemy import text

from app.core.database import Base, SessionLocal, engine
from app.models.core import Company, User, UserCompanyAccess, UserRole
from app.models.customers import Customer
from app.models.groups import AccessLevel, Group, GroupModuleAuthority
from app.models.job_orders import JobOrder, JobOrderPriority, JobOrderStatus
from app.models.licensing import CompanyModule, LicenseType, Module
from app.models.tax import TaxCode
from app.services import billing as billing_svc
from app.services import contracts as contract_svc
from app.services import service_records as sr_svc
from app.services.auth import hash_password

DEMO_PASSWORD = "demo1234"

# key -> (name, description, is_built, enabled_by_default)
# Covers the 19 business-area modules in docs/module-map.md, plus
# "event_logs" -- a Core / Administration capability (the Event Logs
# master, see app/routers/event_logs.py) broken out as its own module
# key so Group Authority can gate it independently of general admin
# access. Commission Management and Integrations (which owns future
# Odoo migration work) are listed for completeness of the control plane
# but left disabled/not built -- deferred at the user's request until
# Service Operations is finalized.
MODULE_CATALOG = [
    ("core_administration", "Core / Administration", True, True),
    ("event_logs", "Event Logs", True, True),
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


# Default Groups and their per-module access matrix (Group Authority).
# name -> description -> {module_key: AccessLevel}. Modules not listed
# for a group default to AccessLevel.NONE (see GroupModuleAuthority).
NONE, VIEW, EDIT, FULL = AccessLevel.NONE, AccessLevel.VIEW, AccessLevel.EDIT, AccessLevel.FULL

GROUP_CATALOG = {
    "Owner / Admin": (
        "Full access to every module. Dennis's OWNER role already grants this "
        "regardless of group -- this group exists so Staff Master shows him as "
        "grouped, and as the template for any future admin hires.",
        {
            key: FULL
            for key in (
                "core_administration",
                "event_logs",
                "customer_management",
                "service_contracts",
                "service_operations",
                "service_records",
                "billing",
            )
        },
    ),
    "Service Team": (
        "Nico (Service & Support Lead) and the support engineers who log and "
        "resolve Job Orders and submit/approve Service Records.",
        {
            "service_operations": FULL,
            "service_records": FULL,
            "service_contracts": FULL,  # incl. excess-usage review; SRV-004 role check still applies
            "customer_management": VIEW,
            "billing": VIEW,
            "core_administration": NONE,
            "event_logs": NONE,  # system-wide audit trail -- Owner/Admin only by default
        },
    ),
    "Sales Team": (
        "Cherish (Sales Manager) -- owns customers and contracts, and is the "
        "SRV-004/SRV-011 backup decider for excess usage.",
        {
            "customer_management": FULL,
            "service_contracts": FULL,
            "service_operations": VIEW,
            "service_records": VIEW,
            "billing": VIEW,
            "core_administration": NONE,
            "event_logs": NONE,
        },
    ),
    "Finance Team": (
        "Billing and invoicing oversight. No staff seeded into this group yet.",
        {
            "billing": FULL,
            "service_contracts": VIEW,
            "customer_management": VIEW,
            "service_operations": NONE,
            "service_records": NONE,
            "core_administration": NONE,
            "event_logs": NONE,
        },
    ),
}


def seed_groups(db, company: Company) -> dict[str, Group]:
    groups = {}
    for name, (description, matrix) in GROUP_CATALOG.items():
        group = Group(company_id=company.id, name=name, description=description)
        db.add(group)
        db.flush()
        for module_key, access_level in matrix.items():
            db.add(
                GroupModuleAuthority(
                    group_id=group.id, module_key=module_key, access_level=access_level
                )
            )
        groups[name] = group
    db.flush()
    return groups


def wipe_data(db):
    """Truncate all app tables for a clean, repeatable demo reset."""
    table_names = [t.name for t in reversed(Base.metadata.sorted_tables)]
    if table_names:
        db.execute(text(f"TRUNCATE TABLE {', '.join(table_names)} RESTART IDENTITY CASCADE"))
    db.commit()


def seed_module_catalog(db):
    """The Module catalog is global (the list of business areas that
    exist); which of them a given company runs is CompanyModule below."""
    for key, name, is_built, _enabled in MODULE_CATALOG:
        db.add(Module(key=key, name=name, is_built=is_built))
    db.flush()


def seed_company_modules(db, company: Company, disabled_keys: set[str] = frozenset()):
    """Per-company module enablement. `disabled_keys` lets a second
    company run a different module mix from the first -- the whole point
    of Module Control being per-company."""
    for key, _name, _is_built, enabled in MODULE_CATALOG:
        on = enabled and key not in disabled_keys
        db.add(
            CompanyModule(
                company_id=company.id,
                module_key=key,
                enabled=on,
                license_type=LicenseType.INCLUDED,
                enabled_at=datetime.now(timezone.utc) if on else None,
            )
        )
    db.flush()


# GST tax codes. Confirmed 2026-09-10: Webmaster is GST-registered and
# its services are standard-rated (SR). The others are seeded inactive-
# ready so a future zero-rated/exempt supply doesn't need a code change.
TAX_CODES = [
    ("SR", "Standard-rated supply", Decimal("9.00")),
    ("ZR", "Zero-rated supply (e.g. export of services)", Decimal("0.00")),
    ("ES", "Exempt supply", Decimal("0.00")),
    ("OS", "Out of scope", Decimal("0.00")),
]


def seed_tax_codes(db, company: Company):
    for code, name, rate in TAX_CODES:
        db.add(
            TaxCode(company_id=company.id, code=code, name=name, rate_percent=rate, is_active=True)
        )
    db.flush()


def logo_data_uri(initials: str, bg: str = "#7a1f2e") -> str:
    """A simple placeholder logo in the company colours (maroon/white),
    stored the same way an uploaded one is: an image data URI on the
    Company record. Dennis can replace it from Company Setup."""
    svg = (
        '<svg xmlns="http://www.w3.org/2000/svg" width="96" height="96" viewBox="0 0 96 96">'
        f'<rect width="96" height="96" rx="20" fill="{bg}"/>'
        '<text x="48" y="63" font-family="system-ui,Segoe UI,Roboto,sans-serif" '
        f'font-size="36" font-weight="700" fill="#ffffff" text-anchor="middle">{initials}</text>'
        "</svg>"
    )
    return "data:image/svg+xml;base64," + base64.b64encode(svg.encode("utf-8")).decode("ascii")


def main():
    Base.metadata.create_all(bind=engine)  # no-op if migrations already applied
    db = SessionLocal()
    try:
        wipe_data(db)

        company = Company(
            name="Webmaster Consultancy Pte Ltd",
            logo=logo_data_uri("WC"),
            # A Singapore tax invoice must show these.
            address="1 Demo Street, #01-01, Singapore 000001",
            gst_registration_no="M9-0000001-2",
        )
        # A second entity, so multi-company is demonstrable rather than
        # just anticipated: its own logo, its own module mix, its own
        # groups, staff, customers and contracts.
        company2 = Company(
            name="Websoft Digital Pte Ltd",
            logo=logo_data_uri("WD", bg="#1a1315"),
            address="2 Demo Street, #02-02, Singapore 000002",
            gst_registration_no="M9-0000002-3",
        )
        db.add_all([company, company2])
        db.flush()

        seed_module_catalog(db)
        seed_company_modules(db, company)
        # The second entity doesn't run service contracts/job orders --
        # a different module mix, controlled per company.
        seed_company_modules(
            db,
            company2,
            disabled_keys={"service_contracts", "service_operations", "service_records"},
        )
        seed_tax_codes(db, company)
        seed_tax_codes(db, company2)
        groups = seed_groups(db, company)
        groups2 = seed_groups(db, company2)

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
        # Staff of the second entity only -- proves staff, groups and
        # data are company-scoped: Priya never sees company 1's records.
        priya = User(
            company_id=company2.id, email="priya@websoft.local",
            hashed_password=hash_password(DEMO_PASSWORD), full_name="Priya (Digital Lead)",
            role=UserRole.SALES_MANAGER,
        )
        db.add_all([dennis, nico, cherish, engineer, priya])
        db.flush()

        # Multi-company access + the Group each person holds IN EACH
        # COMPANY (confirmed 2026-09-10: a Group per company, since
        # Groups are themselves company-scoped). Dennis works across both
        # entities and gets the company switcher -- note he is Owner /
        # Admin in company 1 but only Finance Team in company 2, which is
        # exactly what per-company groups make possible. Everyone else is
        # single-company. (The owner role can reach any company and
        # bypasses Group Authority regardless; the rows make the intent
        # explicit in the data.)
        db.add_all(
            [
                UserCompanyAccess(
                    user_id=dennis.id, company_id=company.id,
                    group_id=groups["Owner / Admin"].id,
                ),
                UserCompanyAccess(
                    user_id=dennis.id, company_id=company2.id,
                    group_id=groups2["Finance Team"].id,
                ),
                UserCompanyAccess(
                    user_id=nico.id, company_id=company.id,
                    group_id=groups["Service Team"].id,
                ),
                UserCompanyAccess(
                    user_id=cherish.id, company_id=company.id,
                    group_id=groups["Sales Team"].id,
                ),
                UserCompanyAccess(
                    user_id=engineer.id, company_id=company.id,
                    group_id=groups["Service Team"].id,
                ),
                UserCompanyAccess(
                    user_id=priya.id, company_id=company2.id,
                    group_id=groups2["Sales Team"].id,
                ),
            ]
        )

        customer = Customer(
            company_id=company.id, name="Acme Manufacturing Pte Ltd",
            billing_email="accounts@acme-mfg.test",
            billing_address="10 Factory Road, Singapore 100010",
            payment_terms_days=30,  # terms vary per customer (confirmed)
        )
        # Company 2's own customer -- switching companies swaps the whole
        # dataset, so this is what Dennis sees under Websoft Digital.
        customer2 = Customer(
            company_id=company2.id, name="Northwind Retail Pte Ltd",
            billing_email="ap@northwind-retail.test",
            billing_address="20 Orchard Lane, Singapore 200020",
            payment_terms_days=14,  # a different customer, different terms
        )
        db.add_all([customer, customer2])
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
            company_id=company.id, customer_id=customer.id, contract_id=contract.id,
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
        print(f"Company 1: {company.name} (logo set)")
        print(f"Company 2: {company2.name} (logo set) -- customer: {customer2.name}")
        print(f"Customer: {customer.name} ({customer.id})")
        print(f"Contract: {contract.id} -- {contract.consumed_minutes}/{contract.contracted_minutes} min consumed")
        print(f"Job order: {job_order.id} -- {job_order.subject}")
        print(f"Pending service record (approve live in demo): {final_record.id} -- {final_record.raw_minutes} raw min -> {final_record.rounded_minutes} rounded min")
        print("\nEnabled modules:", ", ".join(k for k, _, _, e in MODULE_CATALOG if e))
        print("\nGroups:", ", ".join(GROUP_CATALOG.keys()))
        print("\nLogins (all password: demo1234):")
        all_groups = {**{g.id: n for n, g in groups.items()}, **{g.id: n for n, g in groups2.items()}}
        company_names = {company.id: company.name, company2.id: company2.name}
        access_rows = db.query(UserCompanyAccess).all()
        for u in (dennis, nico, cherish, engineer, priya):
            print(f"  {u.email:30s} role={u.role.value}")
            for row in [a for a in access_rows if a.user_id == u.id]:
                marker = " (active)" if row.company_id == u.company_id else ""
                print(
                    f"      {company_names[row.company_id]:32s} "
                    f"group={all_groups.get(row.group_id, '-')}{marker}"
                )
        print(
            "\nDennis has access to both companies -- the switcher appears for him only, and he "
            "holds a different Group in each (Owner / Admin vs Finance Team)."
        )
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()


if __name__ == "__main__":
    main()
