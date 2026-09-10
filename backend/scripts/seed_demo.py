"""
Seed a clean demo dataset for the Websoft Service ERP Solution
Service Operations core slice.

Run with: uv run python scripts/seed_demo.py

Sets up:
- Company: Webmaster Consultancy Pte Ltd
- Users: Dennis (owner), Nico (service_lead), Cherish (sales_manager),
  Wei Ling (support_engineer) -- all password "demo1234"
- Customer: Acme Manufacturing Pte Ltd
- One Active 10-hour contract (SGD 3,000), already invoiced annually
- A ticket with timesheet entries already approved, deliberately left
  just short of exhausting the contract, PLUS one final SUBMITTED
  (not yet approved) entry that will push it into Excess Usage --
  left pending on purpose so a live walkthrough can approve it and
  perform the Nico excess-usage review itself, rather than the seed
  script doing it upfront.
"""
import sys
from datetime import date, timedelta
from pathlib import Path

sys.path.append(str(Path(__file__).resolve().parents[1]))

from sqlalchemy import text

from app.core.database import Base, SessionLocal, engine
from app.models.core import Company, User, UserRole
from app.models.customers import Customer
from app.models.tickets import HelpdeskTicket, TicketPriority, TicketStatus
from app.services import contracts as contract_svc
from app.services import timesheets as ts_svc
from app.services.auth import hash_password
from app.services import billing as billing_svc

DEMO_PASSWORD = "demo1234"


def wipe_data(db):
    """Truncate all app tables for a clean, repeatable demo reset."""
    table_names = [t.name for t in reversed(Base.metadata.sorted_tables)]
    if table_names:
        db.execute(text(f"TRUNCATE TABLE {', '.join(table_names)} RESTART IDENTITY CASCADE"))
    db.commit()


def main():
    Base.metadata.create_all(bind=engine)  # no-op if migrations already applied
    db = SessionLocal()
    try:
        wipe_data(db)

        company = Company(name="Webmaster Consultancy Pte Ltd")
        db.add(company)
        db.flush()

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

        ticket = HelpdeskTicket(
            customer_id=customer.id, contract_id=contract.id,
            subject="Intermittent VPN connectivity for remote staff",
            priority=TicketPriority.HIGH, status=TicketStatus.ASSIGNED,
            assigned_to_user_id=engineer.id,
        )
        db.add(ticket)
        db.flush()

        # Already-approved work totalling 540 of the 600 contracted minutes.
        for i, raw_minutes in enumerate([240, 300]):
            entry = ts_svc.submit_timesheet_entry(
                db, ticket_id=ticket.id, employee_user_id=engineer.id,
                work_date=date.today() - timedelta(days=10 - i * 3), raw_minutes=raw_minutes,
            )
            ts_svc.approve_timesheet_entry(db, entry, ticket, approver=nico)

        db.commit()
        print(f"Consumed so far: {contract.consumed_minutes} / {contract.contracted_minutes} minutes")

        # Final entry left SUBMITTED (not approved) on purpose -- 80 raw
        # minutes rounds to 90 (SRV-007), only 60 remain, so approving this
        # live in the demo will exhaust the contract AND create an Excess
        # Usage record of 30 minutes for Nico to review on camera.
        final_entry = ts_svc.submit_timesheet_entry(
            db, ticket_id=ticket.id, employee_user_id=engineer.id,
            work_date=date.today(), raw_minutes=80,
        )
        db.commit()

        print("\n=== Demo dataset ready ===")
        print(f"Company:  {company.name}")
        print(f"Customer: {customer.name} ({customer.id})")
        print(f"Contract: {contract.id} -- {contract.consumed_minutes}/{contract.contracted_minutes} min consumed")
        print(f"Ticket:   {ticket.id} -- {ticket.subject}")
        print(f"Pending timesheet entry (approve live in demo): {final_entry.id} -- {final_entry.raw_minutes} raw min -> {final_entry.rounded_minutes} rounded min")
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
