# Business Requirements

Placeholder document.

This file will contain the detailed business requirements for Websoft Service ERP Solution,
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

- Websoft Service ERP Solution will replace Odoo through a **phased, module-by-module
  replacement**, not a big-bang cutover.
- Each replaced module will go through a **parallel-run period** alongside
  the corresponding Odoo module before Odoo is retired for that module.
- The order in which business areas are phased in has not yet been decided.

### Historical data from Odoo

- Important historical data currently in Odoo will eventually need to be
  migrated into Websoft Service ERP Solution.
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

## Service Operations Business Rules (CONFIRMED)

Status: **CONFIRMED / DECIDED** (2026-09-04). Unlike most of this document,
the following rules are finalized and are authoritative for Service
Contracts, Helpdesk / Service Operations, Timesheets, and Billing. They
supersede the corresponding open items in
[open-business-decisions.md](open-business-decisions.md), which has been
updated to reflect that — see that document for what remains open.

### SRV-001 — Standard Service Contract Duration — CONFIRMED

- The standard service contract duration is **12 months**.
- Every contract stores a **start date** and an **expiry date**.
- A contract's lifecycle is tracked through the following states:
  **Draft → Active → Exceeded (if applicable) → Expired / Renewed.**
  "Exceeded" reflects a contract that is still within its 12-month period
  but has consumed all of its contracted hours (see SRV-003/SRV-004)
  ahead of expiry.

### SRV-002 — Minimum Contracted Support Hours — CONFIRMED

- The minimum support hours for a normal service contract is **10
  hours**.
- The system must prevent creation of a normal service contract with
  fewer than 10 hours.
- An authorized override mechanism for going below this minimum may be
  defined later, but **who can authorize it and how is not yet
  decided** — tracked in
  [open-business-decisions.md](open-business-decisions.md).

### SRV-003 — No Grace Period — CONFIRMED

- There is **no grace period** for exceeding contracted support hours.
- Once contracted hours are fully consumed, the next unit of support
  usage is immediately **excess usage** — it is not automatically
  absorbed as free/bonus hours.

### SRV-004 — Excess Hours Require Nico's Review — CONFIRMED

- Once a customer reaches or exceeds contracted support hours, further
  support usage must be reviewed by **Nico**, who is responsible for
  Service & Support.
- The system must **not** simply continue deducting excess usage
  automatically from the contract.
- A contract's usable balance can **never become negative**.
- Excess usage is recorded **separately** from normal contract
  consumption and must be clearly visible.
- Nico decides the treatment of each instance of excess usage — for
  example: billable excess support, approved non-billable support, or
  another authorized treatment to be defined later.
- Every such decision, and the reason for it, must be **auditable** (who
  decided, when, what was decided, and why).
- Who reviews excess usage when Nico is unavailable (a backup/delegate)
  is **not yet decided** — tracked in
  [open-business-decisions.md](open-business-decisions.md).

### SRV-005 — Unused Hours Expire Completely — CONFIRMED

- At the end of the 12-month contract period, all unused contracted
  support hours **expire completely**.
- Unused hours do **not**: carry forward automatically, carry forward
  upon renewal, convert into monetary credit, or transfer to another
  contract.
- A renewal creates a **new support-hour allocation** — it does not
  inherit or extend the expiring contract's remaining balance.
- Historical expired hours must remain **visible for reporting and
  audit purposes** (archived, not deleted).

  *Example:* a contract with 20 contracted hours, of which 14 were used,
  has 6 hours remaining at expiry. Those 6 hours become **Expired
  Hours**; the usable balance becomes 0; the renewal contract receives
  its own new allocation.

### SRV-006 — No Unbilled Service Hours — CONFIRMED

- The system must not allow normal service activity to remain
  indefinitely in an "Unbilled Hours" state. Every completed service
  activity must ultimately be accounted for as exactly one of:
  1. Contract hours consumed — no additional invoice required.
  2. Excess hours approved by Nico as billable — must proceed to
     billing/invoicing.
  3. Approved non-billable excess — the reason must be recorded.
  4. Another explicitly approved treatment.
- The system monitors for **"Unaccounted Service Activity"** rather than
  treating unbilled hours as an acceptable permanent state.
- Before a service contract expires, the system should identify: open
  support tickets, missing timesheets, unapproved excess hours, billable
  excess hours not yet invoiced, and other service activities requiring
  review.
- The objective at contract expiry is: **all service activities
  accounted for** — all billable service items processed, and any
  remaining contracted hours expired (per SRV-005).

These rules directly resolve open items 1.2 and 1.3 in
[open-business-decisions.md](open-business-decisions.md), and narrow
(without fully closing) items 1.4 and 1.6 — see that document for what
remains open, including the SRV-002 override mechanism, the pricing/rate
for billable excess hours, and the backup reviewer for SRV-004.

### Service Operations Workflow (CONFIRMED shape)

The end-to-end service workflow these rules govern is:

```
Customer
  → Support Ticket
  → Assignment
  → Service Work
  → Timesheet
  → Contract Hour Validation
  → Contract Deduction OR Excess Review (Nico)
  → Billing Decision
  → Invoice (if billable)
  → Complete / Auditable Record
```

See [workflows.md](workflows.md), Workflow C, for the detailed version of
this workflow, including responsible parties, data created, and
exceptions.

### Service Operations Dashboard Requirements

The Service Operations dashboard should eventually be able to identify:

- Active contracts
- Contracts expiring soon
- Contracted hours
- Used hours
- Remaining usable hours
- Expired hours
- Excess hours
- Excess hours awaiting Nico's review
- Missing timesheets
- Open tickets
- Service activities requiring accounting/billing action
- Renewals required

This is a requirements list, not a design — see
[module-map.md](module-map.md) (Reporting / Management Dashboard) for
where this is expected to live architecturally.

## Conceptual Business Entities

This section lists the major business entities Websoft Service ERP Solution is expected
to eventually need, and describes how they relate to one another
conceptually. This is **not** a database schema — there are no tables,
columns, or keys here. It exists to give a shared vocabulary for the
module structure ([module-map.md](module-map.md)) and workflows
([workflows.md](workflows.md)), and to be refined as detailed requirements
are gathered per module.

### Entity list, by area

**Core / people & organizations**
- Company — a legal entity using the system (Webmaster Consultancy Pte Ltd
  today; the model should not preclude more companies later).
- User — a system login/account.
- Employee — a staff member; may or may not be the same record as a User,
  depending on future decisions.
- Role / Permission — defines what a User can do (RBAC).
- Customer — a company or individual Webmaster does business with.
- Contact — a person associated with a Customer (or Supplier).
- Site — a physical location associated with a Customer (for service
  delivery, hardware installation).
- Supplier — a company Webmaster purchases from.

**CRM & Sales**
- Lead — an unqualified prospective opportunity.
- Sales Opportunity — a qualified, tracked potential sale.
- Quotation — a formal price/scope offer to a Customer.
- Quotation Line — one priced item/service/hardware line within a
  Quotation.
- Sales Order — a confirmed commitment from an accepted Quotation.
- Sales Order Line — one line within a Sales Order.

**Service Contracts & Delivery**
- Contract — a recurring service agreement with a Customer, standard
  duration 12 months (SRV-001), with a stored start/expiry date and a
  lifecycle of Draft → Active → Exceeded (if applicable) → Expired /
  Renewed.
- Contract Line — a specific service/entitlement (e.g. included hours,
  minimum 10 per SRV-002) within a Contract.
- Contract Hour Consumption Record — a record of contracted hours used,
  forming the contract's usable balance, which can never go negative
  (SRV-004).
- Excess Usage Record — a record of support usage beyond contracted
  hours (SRV-003), recorded separately from normal consumption, pending
  or carrying Nico's treatment decision and reason (SRV-004).
- Expired Hours Record — the record of unused contracted hours forfeited
  at contract expiry (SRV-005), retained for reporting/audit.
- Helpdesk Ticket — a logged customer issue or service request.
- Project — a scoped body of work delivered to a Customer.
- Project Task — a unit of work within a Project.
- Timesheet (Entry) — a record of time an Employee spent against a
  Ticket, Project Task, or Contract.

**Commerce & Finance**
- Product / Service (item master) — something Webmaster sells (a
  service, a hardware product, etc.).
- Invoice — a bill issued to a Customer.
- Invoice Line — one billed item within an Invoice.
- Credit Note — a correction/reduction against an Invoice.
- Payment (Customer) — money received from a Customer.
- Purchase Order — a confirmed order to a Supplier.
- Purchase Order Line — one line within a Purchase Order.
- Goods Receipt — a record of goods physically received against a
  Purchase Order.
- Supplier Invoice — a bill received from a Supplier.
- Payment (Supplier) — money paid to a Supplier.
- Journal Entry / General Ledger Account — the financial posting layer
  that records the accounting impact of the above.
- Commission (record) — a calculated, approved, and eventually paid
  commission amount tied to a sale and a salesperson.

**Inventory & Hardware**
- Inventory Item — a stocked item, tracked by quantity at a location.
- Stock Movement — a recorded change in inventory (receipt, issue,
  transfer, adjustment).
- Hardware Asset — an individually serial-tracked unit of hardware, from
  receipt through installation and service life.
- Warehouse / Location — a place where stock or assets are held.

**Cross-cutting**
- Audit Log Entry — a record of a significant action taken on another
  entity (who, when, what changed), supporting the audit-trail
  requirement in [CLAUDE.md](../CLAUDE.md).

### Relationships, conceptually

- A **Company** is the top-level context for nearly everything else
  (Users, Customers, Contracts, Invoices, etc.) — today there is one
  Company, but the model should anticipate more than one in the future.
- A **User** may correspond to an **Employee**; a User has one or more
  **Roles**, which grant **Permissions**.
- A **Customer** has one or more **Contacts** and one or more **Sites**.
  A Customer is "owned" by a salesperson/account owner (rule to be
  decided — see [open-business-decisions.md](open-business-decisions.md)).
- A **Lead**, once qualified, becomes a **Sales Opportunity**, which is
  linked to a Customer (or a not-yet-a-customer prospect) and to a
  Contact.
- A **Sales Opportunity** may lead to one or more **Quotations**, each
  made up of **Quotation Lines** that reference a **Product/Service**.
- An accepted **Quotation** becomes a **Sales Order**, with **Sales Order
  Lines** mirroring the quotation lines (possibly adjusted).
- A **Sales Order** may result in one or more of: a **Contract**, a
  **Project**, and/or **Hardware Assets** being allocated for delivery —
  depending on what was sold.
- A **Contract** has one or more **Contract Lines**, each defining an
  entitlement (e.g. included hours of a given service). A Contract
  belongs to one Customer, and its lifecycle status governs whether
  further consumption is checked, flagged as Exceeded, or blocked because
  it has Expired or been Renewed.
- A **Helpdesk Ticket** belongs to a Customer, optionally references a
  **Hardware Asset**, and is checked against the Customer's active
  **Contract** for entitlement/SLA.
- A **Project** belongs to a Customer (and optionally a Sales Order), and
  is broken into **Project Tasks**.
- A **Timesheet Entry** belongs to an Employee and references exactly one
  of: a Helpdesk Ticket, a Project Task, or (indirectly, via either of
  those) a Contract. An approved entry against a Contract is validated
  against the Contract's remaining balance: if hours remain, it reduces
  the **Contract Hour Consumption Record**; if the contract is already at
  or beyond its entitlement (per SRV-003), it instead creates an
  **Excess Usage Record** for Nico's review rather than reducing the
  balance below zero (SRV-004). At contract expiry, any remaining balance
  becomes an **Expired Hours Record** (SRV-005) rather than being
  consumable further.
- An **Invoice** belongs to a Customer and has one or more **Invoice
  Lines**, each of which may originate from a Sales Order Line, a
  Contract Line (recurring billing), a Timesheet Entry (billable time),
  or a Hardware Asset (hardware sale). A **Credit Note** references an
  Invoice it corrects.
- A **Payment (Customer)** is allocated against one or more Invoices
  (allocation rule to be decided).
- A **Purchase Order** belongs to a Supplier and has one or more
  **Purchase Order Lines**, each referencing a Product/Service or
  Inventory Item. A **Goods Receipt** references a Purchase Order (in
  full or in part) and results in **Stock Movement** records and,
  for serialized items, new **Hardware Asset** records.
- A **Supplier Invoice** references a Purchase Order and Goods Receipt(s)
  it is matched against, and a **Payment (Supplier)** is made against it.
- A **Hardware Asset** originates from a Goods Receipt, is optionally
  allocated to a Sales Order, and is optionally linked to a Customer, a
  Site, a Contract (for coverage), and Helpdesk Tickets raised against it.
- A **Commission** record references a Sales Order (and/or the Invoice/
  Payment that triggers it, per the decision still to be made) and the
  salesperson(s) it is paid to.
- **Journal Entries** are created from Invoices, Payments (customer and
  supplier), Supplier Invoices, and Commission records, to keep the
  General Ledger consistent with operational activity.
- **Audit Log Entries** reference the entity and action they record, and
  are expected to attach to most of the entities above wherever the
  "financial and operational transactions must have audit trails" rule
  in [CLAUDE.md](../CLAUDE.md) applies.

This entity list and its relationships will be refined — and formal data
models/tables designed — once the business decisions in
[open-business-decisions.md](open-business-decisions.md) are resolved and
detailed, per-module requirements are gathered.
