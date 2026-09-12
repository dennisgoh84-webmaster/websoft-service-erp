# Local Development Setup

This covers running the app on your own machine for development. For
standing up a shared server so other staff can test it, see
[DEPLOY.md](DEPLOY.md) instead.

Status: first working slice -- the **Service Operations core** (Company/Individual,
Service Contract, Job Order, Service Record, Excess Usage Review,
Billing/Invoice), plus Module Control / multi-company licensing and a
summary dashboard, implementing the confirmed SRV-001..018 and BILL-001/
002/004/005/006 rules from [docs/business-requirements.md](docs/business-requirements.md).
No other business area has application code yet. Commission Management,
further Service Record business-rule decisions, and Odoo migration
planning are deferred for now (see
[docs/open-business-decisions.md](docs/open-business-decisions.md)).

## Prerequisites

- Python 3.11+, [uv](https://docs.astral.sh/uv/)
- Node.js 20+
- PostgreSQL 16 (local install or any reachable instance)
- LibreOffice Writer, headless-capable (`apt install libreoffice-writer` on
  Debian/Ubuntu) -- only needed for the "Email" button (see Email /
  WhatsApp below), which converts the generated .docx to PDF via
  `soffice --headless --convert-to pdf`. `libreoffice-core`/`-common`
  alone is NOT enough -- without the `-writer` package the conversion
  fails with "source file could not be loaded" (no Writer document
  filter installed). Everything else (Print, Word export, WhatsApp)
  works without this.

## Database

```bash
createuser websoft_app --pwprompt   # password: websoft_dev_local (or your own -- update backend/.env)
createdb websoft_service_erp -O websoft_app
```

## Backend (FastAPI)

```bash
cd backend
uv sync
uv run alembic upgrade head       # apply migrations
uv run python scripts/seed_demo.py   # reset + load demo data (see script docstring)
uv run uvicorn app.main:app --reload --port 8000
```

API docs: http://127.0.0.1:8000/docs

Config is read from environment variables / a local `.env` file (see
`app/core/config.py`); defaults match the database setup above and are
for local development only -- never use the default JWT secret in any
real deployment.

## Frontend (React + TypeScript)

```bash
cd frontend
npm install
npm run dev -- --port 5173
```

Open http://127.0.0.1:5173 -- the dev server proxies `/api` to the
backend on port 8000 (see `vite.config.ts`).

Demo logins (all password `demo1234`, after running `seed_demo.py`):

| Email | Role |
|---|---|
| dennis@websoft.local | owner (also manages Module Control) |
| nico@websoft.local | service_lead (Nico -- SRV-004 excess-usage reviewer) |
| cherish@websoft.local | sales_manager (Cherish -- SRV-011 backup reviewer) |
| weiling@websoft.local | support_engineer |

## Email / WhatsApp on documents

Purchase Order, Service Records, Sales Quotation, Sales Invoice, Receipt
Voucher, Payment Voucher, and Statement of Accounts (on the Sales
Invoice page) can all Email or WhatsApp themselves to the relevant
Company/Individual record -- the customer on the document, or the
supplier for a Purchase Order/Payment Voucher (a supplier is just a
Company/Individual flagged "Is Supplier", not a separate file -- see
docs/open-business-decisions.md #23).

- **Email** sends for real over SMTP, with the document as a PDF
  attachment (converted from the same .docx used for its Word export --
  see `app/services/pdf_convert.py` and `app/services/document_email.py`,
  the shared helper every document type's Email button calls). It is
  unconfigured by default: until `backend/.env` carries real settings,
  the button fails with a clear "Email sending is not configured yet"
  error instead of pretending to send. Add to `backend/.env`:

  ```
  smtp_host=smtp.office365.com
  smtp_port=587
  smtp_username=...
  smtp_password=...
  smtp_from_email=...
  smtp_from_name=Web Master Consultancy
  ```

  One shared mailbox for the whole install, not per-company. Do not
  commit real credentials -- `.env` is gitignored.
- **WhatsApp** opens a `wa.me` chat link pre-filled with a short message
  (no API/account needed) -- you attach the PDF yourself in the chat.
  Needs a phone number set on the relevant Company/Individual record.

## Demo video

`frontend/record_demo.cjs` uses Playwright to script and record a
walkthrough of the confirmed workflow (login -> contract hours ->
approve a Service Record that exhausts the contract -> Nico's
excess-usage review -> resulting invoice). Run `node record_demo.cjs`
from `frontend/` with both servers running; re-run `seed_demo.py` first
for a clean, repeatable recording. The video sent previously predates
the Job Order/Service Record renaming and the dashboard/Module Control
additions -- re-run this script for an up-to-date recording.

## Scope and open decisions

This build intentionally does not cover every module in
[docs/module-map.md](docs/module-map.md) -- only the Service Operations
core slice, plus Module Control and the dashboard. Several pragmatic
implementation defaults were made where a business decision is still
open or deferred in
[docs/open-business-decisions.md](docs/open-business-decisions.md) (e.g.
item 9.1, who approves Service Records -- deferred); these are called out
in code comments (see `app/services/service_records.py`) rather than
silently assumed, and should be revisited once decided.
