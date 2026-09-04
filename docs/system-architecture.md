# System Architecture

Placeholder document.

This file will contain the detailed system architecture for Webmaster ERP,
including the application stack, module boundaries, database design
conventions, authentication/authorization approach, and integration
strategy — consistent with the development rules in the root
[CLAUDE.md](../CLAUDE.md) (modular architecture, PostgreSQL, audit trails,
migrations, etc.).

The high-level stack and architectural direction have now been approved (see
[CLAUDE.md](../CLAUDE.md)). This document records that preliminary
architecture at a conceptual level. It does **not** yet define database
tables, API endpoints, module boundaries in detail, or any other
implementation-level design — those will be developed in follow-up work
before application coding begins.

## Preliminary Architecture

### Frontend — React + TypeScript

- Single-page application built with React and TypeScript.
- Expected to be organized by business module (e.g. CRM, Billing,
  Helpdesk) to keep it maintainable as more modules are added, in line
  with the "modular and maintainable architecture" development rule.
- Detailed component structure, state management approach, and UI library
  choices are not yet decided.

### Backend — FastAPI

- Python backend built with FastAPI.
- Expected to be organized into modules/services aligned with the business
  areas in CLAUDE.md, keeping business logic separate from the API/HTTP
  layer per the development rules.
- Detailed service boundaries, folder structure, and internal layering are
  not yet decided.

### Database — PostgreSQL

- PostgreSQL is the system of record for all business and financial data.
- Schema changes will go through migrations (per the development rules) —
  the specific migration tooling has not yet been chosen.
- No tables or schemas have been designed yet.
- Multi-company support (future) and archival of historical Odoo data
  (future) are expected to influence schema design, but no specific
  approach (e.g. shared schema with company_id, separate schemas, etc.)
  has been decided yet.

### Authentication and role-based access

- The system requires authentication and role-based access control (RBAC)
  for all users.
- Expected to cover distinct roles across business areas (e.g. finance,
  sales, service operations) with different permission levels.
- Specific auth mechanism (e.g. session-based, JWT, SSO/OAuth provider),
  identity provider, and the detailed role/permission model are not yet
  decided.

### Audit logging

- Financial and operational transactions must produce audit trails (per
  the development rules) — who did what, when, and (where relevant) the
  before/after state.
- Records are never permanently deleted; soft-delete/archival is used
  where appropriate instead.
- The specific audit logging mechanism (e.g. application-level audit
  tables, database-level triggers, change-data-capture) has not yet been
  decided.

### File / document storage

- The system will need to store documents/files associated with business
  records (e.g. contracts, invoices, attachments).
- Storage location/technology (e.g. object storage such as S3-compatible
  storage vs. local/VPS disk) has not yet been decided, but the choice
  should keep the architecture portable across cloud providers per the
  approved deployment direction.

### Background jobs

- Some work is expected to run outside the request/response cycle (e.g.
  scheduled reports, data synchronization, sending notifications, future
  Odoo data migration jobs).
- A background job/task queue mechanism will be needed; the specific
  technology has not yet been decided.

### API architecture

- FastAPI backend exposes APIs consumed by the React frontend and
  potentially other future integrations.
- Expected to be organized per business module, versioned appropriately,
  and validated on the backend (per the development rules) in addition to
  frontend validation.
- Whether the API is a single monolithic FastAPI service or split further
  has not yet been decided; a modular monolith is the likely starting
  point given the phased Odoo replacement strategy, but this is not yet
  finalized.

### Integration architecture

- The system will need to integrate with external systems over time,
  including (at minimum):
  - Odoo, during the phased replacement/parallel-run period.
  - InvoiceNow / Peppol, for e-invoicing (future).
  - Other services as identified (e.g. payment, banking, tax reporting).
- Integrations should be designed so individual integrations can be added
  or retired independently as modules are phased in, without requiring
  changes to unrelated parts of the system.
- Specific integration patterns/technology have not yet been decided.

### Deployment architecture

- Initial deployment target is a cloud/VPS environment.
- The architecture should avoid unnecessary coupling to any one
  infrastructure provider, so that it remains portable to AWS, Azure, or
  other infrastructure later.
- Specific deployment tooling (e.g. containerization, orchestration,
  CI/CD pipeline) has not yet been decided.

### Backup and disaster recovery

- Data backup and recovery is a required operational capability.
- Given the financial and operational nature of the data, backups must
  support point-in-time recovery of the PostgreSQL database at minimum.
- Specific backup frequency, retention policy, and disaster recovery
  procedures have not yet been decided.

### Future: Odoo migration

- Odoo will be replaced in phases, module by module, with a parallel-run
  period for each module rather than a big-bang cutover.
- Important historical data will eventually be migrated from Odoo into
  Webmaster ERP; some historical data may be migrated into an archival
  form rather than as fully operational records.
- A dedicated migration approach (e.g. ETL scripts, one-time import jobs,
  ongoing sync during parallel-run) will need to be designed once the
  phasing order and per-module requirements are known.

### Future: InvoiceNow integration

- Singapore's InvoiceNow / Peppol e-invoicing network must eventually be
  supported for invoicing/billing.
- This will require a Peppol Access Point integration (direct or via a
  third-party provider) — not yet selected.
- Detailed design is deferred until the Billing/Accounts Receivable
  business requirements are defined.

### Future: AI integration

- "AI Assistant" is listed as an initial candidate business area in
  CLAUDE.md.
- Any AI integration will need to respect PDPA and the system's audit
  trail and access-control requirements (e.g. controlling what business
  data an AI feature can access or act on).
- No specific AI capabilities, providers, or integration points have been
  decided yet.
