# Business Requirements

Placeholder document.

This file will contain the detailed business requirements for Webmaster ERP,
covering the business areas listed in the root [CLAUDE.md](../CLAUDE.md)
(CRM, Sales, Customer Management, Service Contracts, Helpdesk, Service
Operations, Projects, Timesheets, Billing, Accounts Receivable, Accounts
Payable, Purchasing, Inventory, Hardware Management, Commission Management,
Management Reporting, AI Assistant).

No business workflows or rules have been defined yet. Detailed requirements
will be gathered and documented here before any application coding begins.

## Project-Level Requirements (Approved)

These are project-level requirements approved alongside the architecture
decisions in the root [CLAUDE.md](../CLAUDE.md). They are not detailed
business workflows — those are still to be gathered per business area —
but they set boundaries that the detailed requirements and architecture
must respect.

### Odoo replacement strategy

- Webmaster ERP will replace Odoo through a **phased, module-by-module
  replacement**, not a big-bang cutover.
- Each replaced module will go through a **parallel-run period** alongside
  the corresponding Odoo module before Odoo is retired for that module.
- The order in which business areas are phased in has not yet been decided.

### Historical data from Odoo

- Important historical data currently in Odoo will eventually need to be
  migrated into Webmaster ERP.
- Not all historical data needs to remain fully operational — older data
  may be migrated into an **archival** form rather than into live,
  actively-used records.
- Which data is "important", which is archival-only, and the exact
  migration scope/order have not yet been decided.

### Multi-company

- The initial implementation is for **Webmaster Consultancy Pte Ltd only**.
- Business requirements and workflows should be captured in a way that does
  not assume a single company is hard-coded forever, since the system is
  expected to support multiple companies/entities in the future.
- No specific additional companies/entities have been identified yet.

### Singapore regulatory and operational requirements

The following must be anticipated by both business requirements and
architecture, even though detailed workflows are not yet defined:

- **GST** — Goods and Services Tax handling (e.g. on invoices, billing).
- **InvoiceNow / Peppol** — Singapore's e-invoicing network.
- **PDPA** — Personal Data Protection Act compliance for personal data
  handling.
- **Financial audit trails** — required for financial and operational
  transactions (see also the Development Rules in [CLAUDE.md](../CLAUDE.md)).
- **Role-based access control** — required for authentication/authorization
  across the system.
- **Data backup and recovery** — required as an operational capability.

These are constraints to design for, not yet fully specified requirements.
Detailed rules for each (e.g. GST rates/treatment, specific PDPA data
handling procedures) are still to be gathered.
