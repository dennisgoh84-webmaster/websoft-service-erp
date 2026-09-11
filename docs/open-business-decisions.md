# Business Decisions Required From Webmaster

This document lists business rules and decisions that **cannot be safely
assumed** and must be decided by Dennis (or whoever Webmaster Consultancy
designates) before the affected areas can be designed in detail.

Per the CLAUDE.md development rule "Never assume a business rule when
requirements have not been provided," none of these have been decided on
Webmaster's behalf. Where [workflows.md](workflows.md) or
[module-map.md](module-map.md) describe a proposed process, any point that
depends on one of these decisions is described in general/optional terms
and flagged back to this document.

Each item below notes where it arises, so a decision can be traced to its
impact. This list is expected to grow as detailed requirements gathering
continues per module — it is not necessarily exhaustive yet.

Status legend: **OPEN** (undecided), **DECIDED** (resolved — see the
pointer for where the rule is documented), or **PARTIALLY DECIDED** (the
overall approach is decided but a sub-detail remains open — the open
sub-detail is called out explicitly).

---

## 1. Service Contracts & Hours

1.1. **How do service contracts calculate consumed hours?**
   **Status: DECIDED — SRV-007.** Each service record is rounded up to
   the nearest 15 minutes before deduction from the contract balance. See
   [business-requirements.md](business-requirements.md#service-operations-business-rules-confirmed).
   *Arises in:* Service Contracts, Service Records; Workflow C.

1.2. **Do unused contract hours expire, roll over, or get forfeited** at
   the end of a contract period, and if they roll over, is there a cap?
   **Status: DECIDED — SRV-005.** Unused hours expire completely at the
   end of the 12-month contract period: no automatic carry-forward, no
   carry-forward on renewal, no conversion to credit, no transfer to
   another contract. See
   [business-requirements.md](business-requirements.md#service-operations-business-rules-confirmed).
   *Arises in:* Service Contracts; Workflow I.

1.3. **What happens when contract hours are exhausted mid-contract?**
   **Status: DECIDED — SRV-003 and SRV-004.** There is no grace period;
   the contract balance is never reduced below zero; the next unit of
   usage beyond entitlement becomes Excess Usage requiring Nico's
   (Service & Support) review and decision, recorded and auditable. The
   system does not auto-continue deducting and does not auto-bill without
   that review. See
   [business-requirements.md](business-requirements.md#service-operations-business-rules-confirmed).
   *Arises in:* Service Contracts, Helpdesk / Service Operations, Billing;
   Workflow C.

1.4. **How is support/work beyond contract entitlement billed?**
   **Status: DECIDED — SRV-008.** Billable excess usage is charged at the
   contract's own blended rate (contract value ÷ contracted hours); no
   customer pre-approval is required before invoicing — the customer is
   billed then notified.
   *Arises in:* Billing, Helpdesk / Service Operations; Workflow C.

1.5. **What SLA terms apply, and how are SLA breaches handled?**
   **Status: DECIDED (deferred) — SRV-009.** No formal SLA response/
   resolution targets are defined at this time; this is an explicit
   decision to defer, not an open gap. Job Order priority and timestamps
   are still tracked so targets can be added later without a data-model
   change.
   *Arises in:* Service Contracts, Helpdesk / Service Operations;
   Workflow C.

1.6. **Does contract renewal create a new contract record or extend the
   existing one**, and how is a coverage gap (if renewal is late) handled?
   **Status: DECIDED — SRV-010/SRV-016.** Renewal creates a new Contract
   record (referencing the prior one for history), backdated to
   immediately follow the prior contract's expiry so there is no coverage
   gap — as long as renewal happens within **2 weeks** of expiry
   (SRV-016; see item 1.12). Beyond that window it is not backdated (see
   item 1.13 for what happens then).
   *Arises in:* Service Contracts; Workflow I.

1.7. **Is a customer credit check or credit limit required before
   activating a new contract?**
   **Status: DECIDED — SRV-017.** Not required for now; contracts
   activate based on the commercial/sales agreement alone.
   *Arises in:* Service Contracts, Customer Management; Workflow B.

1.8. **Who is the backup/delegate reviewer for excess usage when Nico is
   unavailable?**
   **Status: DECIDED — SRV-011.** Cherish (Sales Manager) is the confirmed
   backup reviewer; the same recording/auditability requirements apply
   to her decisions as to Nico's.
   *Arises in:* Service Contracts, Helpdesk / Service Operations;
   Workflow C.

1.9. **What is the authorized override mechanism for a service contract
   below the SRV-002 minimum of 10 hours?**
   **Status: DECIDED — SRV-012.** There is no override mechanism; 10
   hours is a hard minimum with no exceptions until Dennis decides
   otherwise.
   *Arises in:* Service Contracts, Sales; Workflow B.

1.10. **What other treatments (beyond billable excess / approved
   non-billable excess) may apply to excess usage under SRV-004/SRV-006,
   and what rules govern each?**
   **Status: DECIDED — SRV-013.** Two further categories are confirmed:
   Warranty / Goodwill, and Internal Write-off. Both require the same
   recorded, auditable reason as any other treatment under SRV-004.
   *Arises in:* Service Contracts, Billing; Workflow C.

1.11. **What lead time before contract expiry should the SRV-006
   pre-expiry accounting check (open job orders, missing service records,
   unapproved/unbilled excess) begin?**
   **Status: DECIDED — SRV-014.** The check begins 30 days before a
   contract's expiry date.
   *Arises in:* Service Contracts, Reporting; Workflow I.

1.12. **What is the maximum window after expiry within which a renewal
   still qualifies for seamless (backdated, no-gap) coverage under
   SRV-010?**
   **Status: DECIDED — SRV-016.** The maximum window is **2 weeks**. A
   renewal within 2 weeks of expiry is backdated to avoid a coverage gap;
   beyond 2 weeks, it's treated as a fresh, non-contiguous contract (see
   item 1.13 for what happens in that later case).
   *Arises in:* Service Contracts; Workflow I.

1.13. **How is a renewal handled if it happens more than 2 weeks after
   expiry** (per SRV-016)?
   **Status: DECIDED — SRV-018.** No fixed rule; handled case-by-case by
   Nico, Cherish, or Dennis.
   *Arises in:* Service Contracts, Helpdesk / Service Operations;
   Workflow I.

## 2. Billing & Invoicing

2.0. **Is the company GST-registered, and how is GST applied?**
   **Status: DECIDED (2026-09-10).** Webmaster Consultancy is
   GST-registered and its services are **standard-rated** (tax code SR,
   currently 9%). Invoices are tax invoices showing the supplier's name,
   address and GST registration number, a serial invoice number, and the
   net / GST / total split. The rate is held in a tax code table rather
   than hard-coded, so a rate change is a configuration change, and each
   invoice stores the rate it was raised at. Zero-rated (ZR), exempt (ES)
   and out-of-scope (OS) codes exist for future use but nothing is
   assumed to use them yet.
   *Arises in:* Billing, Accounts Receivable, Finance / Accounting.

2.1. **What is the recurring billing cycle for contracts?**
   **Status: DECIDED — BILL-001.** Annual upfront — the full 12-month
   contract value is billed at contract start/renewal.
   *Arises in:* Billing, Service Contracts.

2.2. **What invoice approval rules apply** before an invoice is issued to
   a customer?
   **Status: DECIDED — BILL-002.** No approval required; invoices issue
   directly.
   *Arises in:* Billing.

2.3. **What is the credit note approval process** (who can approve, at
   what value)?
   **Status: PARTIALLY DECIDED — BILL-003.** Finance or Cherish approves
   routine credit notes; above a value threshold, Dennis approves. **Still
   OPEN:** the exact threshold (see item 2.7).
   *Arises in:* Billing.

2.4. **What billing method applies to projects**?
   **Status: DECIDED — BILL-004.** Fixed price / milestone billing.
   *Arises in:* Billing, Projects; Workflow D.

2.5. **When is revenue recognized** for contracts, projects, and hardware
   sales?
   **Status: DECIDED — BILL-005.** On invoice, for all three.
   *Arises in:* Billing, Finance / Accounting; Workflows B, D, G.

2.6. **How are quotations internally approved** before being sent to a
   customer?
   **Status: DECIDED — BILL-006.** Cherish (Sales Manager) approves every
   quotation — no threshold exemption.
   *Arises in:* Sales; Workflow A.

2.7. **What is the value threshold above which a credit note requires
   Dennis's approval** (per BILL-003)?
   **Status: STILL OPEN**, but not blocking: like the write-off
   threshold, this is a configurable field in Company Setup, unset by
   default, and while unset the owner approves.
   *Arises in:* Billing.

## 3. Payments & Accounts Receivable

3.0. **What payment terms apply to customer invoices?**
   **Status: DECIDED (2026-09-10).** Terms **vary per customer** — there
   is no company-wide default. `payment_terms_days` is set on each
   customer record and drives the invoice due date and AR aging. A
   customer with no agreed terms gets invoices with **no due date**
   rather than an invented one, and those invoices age as "current"
   until terms are agreed.
   *Arises in:* Accounts Receivable, Billing, Customer Management.

3.1. **How are customer payments allocated** when a payment does not
   exactly match one invoice, or covers multiple invoices?
   **Status: DECIDED — AR-001.** Finance specifies the allocation
   manually, based on remittance information — no automatic rule.
   *Arises in:* Accounts Receivable; Workflow H.

3.2. **What is the write-off / bad debt process**, and who approves it?
   **Status: PARTIALLY DECIDED — AR-002.** Finance can write off small
   amounts directly; above a threshold, Dennis approves. **Still OPEN:**
   the exact threshold (see item 3.4).
   *Arises in:* Accounts Receivable; Workflow H.

3.3. **What happens to an invoice under dispute?**
   **Status: DECIDED — AR-003.** It continues through normal
   collections/aging; no automatic hold.
   *Arises in:* Accounts Receivable, Billing; Workflow H.

3.4. **What is the value threshold above which a write-off requires
   Dennis's approval** (per AR-002)?
   **Status: STILL OPEN**, but no longer blocking: the threshold is a
   configurable field in Company Setup rather than a hard-coded number.
   Until Dennis sets one, the system requires the **owner's approval for
   every write-off** — the safe reading of an undecided rule.
   *Arises in:* Accounts Receivable.

## 4. Purchasing & Accounts Payable

4.1. **What purchase order approval thresholds apply?**
   **Status: PARTIALLY DECIDED — PUR-001.** Value-based: below a
   threshold, procurement/finance approve directly; above it, Dennis
   approves. **Still OPEN:** the exact threshold (see item 4.4).
   *Arises in:* Purchasing; Workflow F.

4.2. **Is 2-way or 3-way matching required** for supplier invoices?
   **Status: DECIDED — PUR-002.** 2-way matching (PO + invoice only); no
   separate goods-receipt match required.
   *Arises in:* Accounts Payable, Purchasing; Workflow F.

4.3. **What is the supplier invoice approval process** before payment is
   released?
   **Status: DECIDED — PUR-003.** Auto-approved once the invoice matches
   the PO (per PUR-002); a mismatch is an exception (handling not yet
   decided — see item 4.5).
   *Arises in:* Accounts Payable; Workflow F.

4.4. **What is the value threshold above which a purchase order requires
   Dennis's approval** (per PUR-001)?
   **Status: STILL OPEN**, but not blocking: a configurable field in
   Company Setup, unset by default, owner approves while unset.
   *Arises in:* Purchasing.

4.5. **How are PO/invoice matching mismatches handled** under the PUR-002
   2-way match (e.g. price or quantity discrepancy)?
   **Status: STILL OPEN, not blocking.** A mismatch (different supplier,
   amount, or an unapproved PO) is recorded as an **exception** with the
   specific discrepancy spelled out, and a bill in that state cannot be
   paid. What happens next — who resolves it, whether it needs a revised
   PO or a credit note — is not decided, so nothing beyond flagging it is
   automated.
   *Arises in:* Accounts Payable, Purchasing; Workflow F.

## 4b. Accounting & Finance (raised 2026-09-10 while building AR)

4b.1. **What is Webmaster's financial year end?** Needed before any
   period close, financial statements, or year-based reporting.
   **Status: mechanism built, date still open.** Accounting Periods
   (`app/models/periods.py`) are plain date ranges an owner/Finance
   defines per company, with no calendar-year assumption baked into the
   backend — so whatever FY end Dennis eventually confirms just becomes
   a period row, not a code change. Confirmed 2026-09-11: until that's
   decided, a date with no period defined at all is unrestricted
   (periods are opt-in protection, not a retroactive block).
   *Arises in:* Finance / Accounting, Reporting.

4b.2. **Which account does each transaction post to?** The chart of
   accounts exists, and the General Ledger + Journal Voucher (JV) are
   now built — but which account a *sales invoice*, a *receipt*, or a
   *bad-debt write-off* posts to automatically is **still not decided**,
   so nothing posts on its own yet. Today the JV is manual: whoever
   raises it picks the accounts. Automatic posting from AR/AP/Billing
   is future work once this is confirmed.
   *Arises in:* Finance / Accounting, Billing, Accounts Receivable.

4b.3. **Is annual-upfront contract revenue deferred and released monthly,
   or taken entirely on invoice?** BILL-005 says revenue is recognized on
   invoice, which suggests the latter, but a 12-month contract billed
   upfront is the classic deferred-revenue case and the two readings give
   very different monthly figures. A "Deferred revenue" account has been
   seeded but is unused pending this decision.
   *Arises in:* Finance / Accounting, Billing.

4b.4. **How are GST returns (F5) prepared and filed**, and over what
   accounting periods? Output tax is captured per invoice, but the return
   itself is not built.
   **Status: partially addressed 2026-09-11.** Accounting Reports →
   Analysis → GST Return now totals output tax (sales, by tax code) vs
   input tax (purchases) for a chosen date range, tax point = invoice
   date. It is read-only: it does not file anything with IRAS, does not
   post to the GL, and does not attempt bad-debt relief on written-off
   invoices (a separate IRAS scheme). The actual filing workflow is
   still open.
   *Arises in:* Finance / Accounting, Integrations.

4b.7. **Year-End Closing mechanics** (raised implicitly by 4b.1;
   confirmed 2026-09-11 in response to an explicit scope question, since
   "what does closing a year actually do" is exactly the kind of thing
   never to assume): Year-End Closing posts one balanced journal entry
   moving every Revenue/Expense account's *movement for the fiscal
   year* (not its all-time balance) into an Equity account the owner
   picks at the time — there is no hardcoded "Retained Earnings"
   account name; the Chart of Accounts' `3100 Retained earnings` is
   simply the obvious seeded choice. Owner-only. Requires every
   Accounting Period tagged with that fiscal year to already be closed.
   Reversible the same way any posted voucher is corrected (General
   Ledger → Reverse) — there is deliberately no separate "unclose"
   mechanism. See `app/services/periods.py` close_fiscal_year.
   *Arises in:* Finance / Accounting.

4b.5. **Does Webmaster ever invoice in a currency other than SGD?**
   Everything is SGD today; multi-currency has not been requested and is
   not assumed.
   *Arises in:* Billing, Finance / Accounting.

4b.6. **What is the invoice number format?** IRAS requires serial
   numbering but no particular layout. The system currently uses
   `INV-<year>-<0001>`, chosen as a convention rather than a decision —
   easily changed.
   *Arises in:* Billing.

## 5. Inventory & Hardware

5.1. **What stock adjustment rules apply?**
   **Status: DECIDED — INV-001.** Requires manager approval before
   taking effect.
   *Arises in:* Inventory.

5.2. **What inventory valuation method is used?**
   **Status: DECIDED — INV-002.** Weighted average cost.
   *Arises in:* Inventory, Finance / Accounting; Workflow G.

5.3. **Does hardware installation require customer sign-off/acceptance**
   before it is considered complete (and billable)?
   **Status: DECIDED — HW-001.** Yes, customer sign-off is required;
   internal confirmation alone is not sufficient.
   *Arises in:* Hardware Management; Workflow G.

5.4. **What is the RMA / hardware failure and replacement process**?
   *Arises in:* Hardware Management, Inventory; Workflow G.

5.5. **What warranty terms apply to hardware**, and how are they tracked
   and enforced?
   *Arises in:* Hardware Management; Workflow G.

## 6. Commission Management

Status: **DEFERRED** (2026-09-10, at Dennis's request) — Commission
Management is not being worked on for now; the items below are parked
until Service Operations (and related areas) are finalized, then
revisited.

6.1. **How are commissions calculated?**
   e.g. flat percentage, tiered by volume, product-specific rates, split
   commissions across multiple salespeople.
   *Arises in:* Commission Management; Workflow E.

6.2. **When does commission become payable** — on sales order
   confirmation, on invoicing, or on customer payment received?
   *Arises in:* Commission Management, Accounts Receivable; Workflow E.

6.3. **Who approves commission calculations**, and is multi-level
   approval required above certain amounts?
   *Arises in:* Commission Management; Workflow E.

6.4. **What is the clawback rule** if a sale is later cancelled or
   refunded after commission was calculated or paid?
   *Arises in:* Commission Management; Workflow E.

6.5. **How is commission paid out** — via payroll, via a
   finance-administered payout, or another mechanism? (This also affects
   whether a payroll/HR integration or module is eventually needed.)
   *Arises in:* Commission Management; Workflow E.

## 7. Projects

7.1. **What is the project budget overrun process** — does a project need
   re-approval if it exceeds budget, and who approves?
   *Arises in:* Projects; Workflow D.

7.2. **What labour cost rate is used for project cost tracking** (e.g.
   standard cost per role, actual salary-based cost)?
   *Arises in:* Projects, Service Records, Finance / Accounting; Workflow D.

7.3. **Who approves milestone completion** for milestone-based billing?
   *Arises in:* Projects, Billing; Workflow D.

## 8. Ownership & Permissions

8.1. **How is customer ownership defined and enforced?**
   e.g. can only the assigned account owner edit/view a customer record,
   or is it open to a wider team?
   *Arises in:* Customer Management.

8.2. **How is sales ownership defined?**
   e.g. what happens to ownership when an opportunity or account is
   reassigned, and how are ownership disputes (two reps claiming a deal)
   resolved?
   *Arises in:* CRM, Sales, Commission Management.

8.3. **How is service ownership defined** for ongoing contracts/job orders
   (e.g. a named account engineer vs. a shared team queue)?
   *Arises in:* Service Contracts, Helpdesk / Service Operations.

8.4. **What are the detailed user roles and permission levels** across the
   system (beyond "authentication and RBAC are required")? e.g. what can a
   support engineer see/edit vs. a finance user vs. a manager.
   **Status: DECIDED (2026-09-10)** — "Group Authority", confirmed with
   Dennis:
   - Every staff member (Staff Master) belongs to **exactly one Group
     per company they work in** (refined 2026-09-10 when multi-company
     went in: Groups are company-scoped, so the assignment lives on the
     staff member's company-access row and the same person can hold a
     different Group in each entity).
   - Each Group has an access level per module: **None / View / Edit /
     Full**. None of the module is hidden; View is read-only; Edit allows
     create/update within the module; Full additionally allows its
     sensitive lifecycle actions (e.g. activating/renewing a contract,
     approving a service record, deciding excess usage, toggling module
     licensing).
   - This is deliberately a **separate axis** from the specific
     named-responsibility rules already confirmed elsewhere (e.g.
     SRV-004/SRV-011: Nico, or Cherish as backup, decides excess usage;
     Dennis as owner). Those rules stay keyed off the small fixed `role`
     field on a user (owner/service_lead/sales_manager/support_engineer/
     finance) and are enforced in addition to, not instead of, Group
     Authority — a user needs both the Group's access level AND (where a
     rule names a role) the matching role to perform that specific action.
   - The owner role always has Full access to every module regardless of
     group, so the owner can never be locked out by a misconfigured Group.
   - Default Groups seeded for the demo: Owner / Admin, Service Team,
     Sales Team, Finance Team — see `backend/scripts/seed_demo.py` for the
     starting matrix; Dennis can create/edit Groups and their matrix from
     the Group Authority admin page, and assign staff to Groups from
     Staff Master.
   *Arises in:* Core / Administration — this affects every module.

## 9. Service Records & Approval

9.1. **Who approves submitted service records**, and within what time frame
   (e.g. weekly approval by a direct manager)?
   **Status: DEFERRED** (2026-09-10, at Dennis's request) — not being
   decided for now. The current build uses a pragmatic default (any user
   with role service_lead, sales_manager, or owner can approve) purely so
   the application functions end-to-end; this is not a business decision
   and should be revisited when this area is finalized.
   *Arises in:* Service Records; Workflows C, D.

9.2. **How is time classified as billable, non-billable, or
   contract-covered**, and can staff choose, or is it determined by the
   job order/project/contract context automatically? **Status: PARTIALLY
   DECIDED** — SRV-003/SRV-004 confirm that the contract balance itself
   determines whether logged time is contract-covered or Excess Usage
   requiring Nico's review; still open is how billable vs. non-billable
   is classified once work is not tied to a contract at all (e.g. pure
   project time).
   *Arises in:* Service Records, Helpdesk / Service Operations, Projects,
   Service Contracts; Workflow C.

9.3. **What is the expected timeframe for submitting service records**, such
   that a "missing service record" can be flagged?
   **Status: DECIDED — SRV-015.** Service Records must be submitted within 3
   business days of the work being performed; a service record not submitted
   within that window is flagged as missing, feeding the SRV-014
   pre-expiry check and the Service Operations dashboard.
   *Arises in:* Service Records, Service Contracts; Workflow C, Workflow I.

## 10. Data & Scope (carried over from business requirements)

Status: **DEFERRED** (2026-09-10, at Dennis's request) — Odoo migration
planning is parked for now; revisit once Service Operations (and related
areas) are finalized.

10.1. **Which historical Odoo data is "important" and must be migrated
   as fully operational**, versus which can be archived in a read-only/
   reference form?
   *Arises in:* Integrations, all modules with historical data; see also
   [business-requirements.md](business-requirements.md).

10.2. **What is the phasing order for module-by-module Odoo replacement**
   (which module goes first, and what defines "ready to cut over" for
   each)?
   *Arises in:* Integrations, all modules.

## 11. Sales (Quotations & Product Catalog, raised 2026-09-10)

11.1. **How should a Sales Quotation's mixed-unit line items map onto a
   Service Contract's required hours**, when the quotation is accepted?
   **Status: DECIDED (2026-09-10).** There are two kinds of Contract
   (`ContractKind`): SERVICE_SUPPORT (hours-based, SRV-002/012's
   10-hour minimum applies) and ANNUAL (a term-only contract, e.g. an
   annual software warranty/maintenance contract -- a value and a
   12-month duration, no hours at all). A quotation's lines split by
   unit of measure: "Hours"/"Hour" lines become one SERVICE_SUPPORT
   contract (summed hours + their value); every other line becomes one
   ANNUAL contract (summed value). A mixed quotation converts to BOTH,
   never blending the two. Job Orders/Service Records can be logged
   against an ANNUAL contract same as any other -- there is just
   nothing to deduct or exceed (`ServiceRecordOutcome.NOT_HOUR_METERED`).
   *Arises in:* Sales, Service Contracts, Billing.
   *Where implemented:* `app/models/contracts.py` (ContractKind),
   `app/models/quotations.py`, `app/services/quotations.py`,
   `app/services/service_records.py`.

11.2. **Should an accepted quotation ever auto-create an Invoice**
   directly (as an alternative or in addition to the Contract
   conversion above), e.g. for one-off product/hardware lines that
   aren't a service contract at all?
   *Arises in:* Sales, Billing, Hardware Management (deferred, section
   5).

## 12. Support/Sales/Dev Monitoring Dashboards & Software Task (raised 2026-09-10)

Reference: a legacy "Monitoring Support" screen (screenshot shared
2026-09-10) showing per-support-staff workload (Job Orders, service
records, contract hours) plus several features/terms not yet built.

12.1. **Software Task** -- confirmed 2026-09-10: "a Software Task that
   is assigned to Support Staff for Testing but not yet tested by the
   staff" (the legacy screen's "Un-Test S/T"). This is a distinct
   entity from Job Order/Service Record -- an assignable task with its
   own testing/verification workflow -- used by both the Support
   monitoring dashboard and the future Software Development dashboard.
   **Status: not yet modeled or built.** Needs its own scoping
   (fields, who creates it, what "tested" means, states beyond
   tested/untested) before building -- deliberately left out of the
   first Support Monitoring dashboard (`app/services/monitoring.py`)
   rather than guessed.
   *Arises in:* Support Monitoring, Software Development (new area,
   not in the original module map).

12.2. **Sales Department monitoring dashboard** and **12.3. Software
   Development monitoring dashboard** -- both mentioned 2026-09-10 as
   needed alongside Support Monitoring, no requirements gathered yet
   (what they should show, and for Dev, how Software Task fits in).
   *Arises in:* Sales, Software Development (new area).

12.4. **Several legacy-screen elements were intentionally left out of
   the first Support Monitoring build**, not yet understood well
   enough to implement correctly: "Support Tool", "Job Schedule",
   "Incident Enquiry", "Phone Call Back" (a customer callback queue),
   and "Projects / OD" (Projects is itself a deferred module -- section
   7). Revisit if/when Dennis wants any of these.

## 13. Contract Type, Product Coverage, Sales Staff (raised 2026-09-11)

13.1. **Third Contract Type -- Ad Hoc Rate.** **Status: DECIDED
   2026-09-11.** `ContractKind` now has three values, each with its own
   offset method: SERVICE_SUPPORT deducts hours from a pool, ANNUAL is
   time coverage only (a term and a value, no hours), and AD_HOC has
   neither -- it stores only a reference hourly rate (no upfront
   value, `contract_value_sgd` forced to 0). Confirmed: nothing is
   auto-deducted or auto-invoiced off an Ad Hoc contract's rate --
   Job Orders/Service Records can still be logged against it for
   history (same "logged but not deducted" pattern already used for
   ANNUAL), and billing off the reference rate is entirely manual.
   *Where implemented:* `app/models/contracts.py` (`ContractKind.AD_HOC`,
   `Contract.hourly_rate_sgd`), `app/services/contracts.py`
   (`create_contract`), `app/services/service_records.py`.
   *Arises in:* Service Contracts, Billing.

13.2. **Product Coverage and Sales Staff on a Contract.** **Status:
   DECIDED 2026-09-11.** A Contract can be linked to zero or more
   catalog Products (`ContractProduct`, many-to-many) and optionally
   to one Sales Staff user (`Contract.sales_staff_id`, any user, not
   restricted to the sales_manager role). Both are editable after
   creation via `PATCH /api/contracts/{id}`, audited like any other
   contract change. Renewal carries both forward from the prior
   contract by default.
   *Where implemented:* `app/models/contracts.py` (`ContractProduct`),
   `app/routers/contracts.py` (`update_contract`).
   *Arises in:* Service Contracts, Sales, Commission Management
   (deferred -- a Sales Staff field on Contract is a likely input to a
   future commission calculation, but no commission rule has been
   confirmed yet).

13.3. **Coverage-date filtering -- judgment call, not explicitly
   confirmed.** "Coverage date" on the main Contracts screen was built
   as an overlap filter against the contract's existing
   `start_date`/`end_date` (same semantics as the Operations Reports
   Contracts report), rather than a new field. Flagging in case a
   different meaning was intended (e.g. filtering by original contract
   *start* date only).
   *Arises in:* Service Contracts.

13.4. **Contract serial/document number.** **Status: DECIDED 2026-09-11**
   (superseded the "not built" note below -- see 14.2: Dennis confirmed
   "all main documents need to have a system generated running
   number," which covers this).
   *Arises in:* Service Contracts, Document Control.

## 14. Calendar-period filtering and universal document numbering (raised 2026-09-11)

14.1. **"Period from / Period to" filter convention.** **Status:
   DECIDED 2026-09-11.** Every FROM/TO date-RANGE filter in the app
   (Contracts' Coverage, Operations Reports, Accounting Reports'
   From/To, Event Logs) now uses a native month picker (`<input
   type="month">`, e.g. "2026-08") instead of an exact-day date
   picker -- "Period from" resolves to the 1st of that month, "Period
   to" to its last day, before being sent to the existing date-range
   query params (no backend filter contract changed). A single
   point-in-time filter (Accounting Reports' Trial/AR/AP Aging "As
   at") is NOT part of this convention and stays an exact-day picker,
   since a period doesn't make sense for one instant -- same for every
   ordinary form field that records one date on a document (start
   date, due date, effective date, work date, etc.), which was left
   untouched.
   One trade-off flagged rather than silently exempted: Event Logs is
   a forensic/audit tool where day-level precision has real
   investigative value, and this change means it can now only be
   filtered down to a month, not a specific day. Applied uniformly
   per the "all filtering" instruction rather than guessed as an
   exception -- easy to revert (`frontend/src/pages/EventLogsPage.tsx`)
   if day-level filtering turns out to be needed.
   *Where implemented:* `frontend/src/lib/period.ts` (shared
   `monthStartISO`/`monthEndISO`/`isoToMonth` helpers), `ContractsPage`,
   `OperationsReportsPage`, `AccountingReportsPage`, `EventLogsPage`.
   *Arises in:* Service Contracts, Operations Reports, Accounting
   Reports, Event Logs -- and every future list/report screen with a
   date-range filter, which should follow the same convention.

14.2. **Universal document numbering.** **Status: DECIDED 2026-09-11**
   -- "all main documents need to have a system generated running
   number to be controlled." Contract, Job Order and Service Record
   (the three operational documents with none) now get one via the
   same `DocumentSequence`/`next_document_number` mechanism as every
   accounting document (CON-/JO-/SR-<year>-<seq>). Existing rows were
   backfilled (oldest first per company/year) in the same migration
   that added the columns, and Document Control (already generic)
   picks the three new counters up automatically.
   *Where implemented:* `app/services/numbering.py` (PREFIXES),
   `app/models/{contracts,job_orders,service_records}.py`,
   migration `1c0caa9bdbb3`.
   *Arises in:* Service Contracts, Service Operations, Service
   Records, Document Control.

## 15. Document number format customization and staff photos (raised 2026-09-11)

15.1. **Document Control: customizable prefix and digit padding.**
   **Status: DECIDED 2026-09-11.** Each document kind's running number
   now has a per-company format, editable from Document Control:
   prefix ("front alphabet"), digit padding (e.g. 4 -> "0001"), and
   whether the year is included. A kind nobody has customized keeps
   using the built-in default (PREFIXES in `app/services/numbering.py`,
   4 digits, year included) -- adding this changed nothing for anyone
   who doesn't touch it. A format change only affects numbers issued
   from that point on; every document already numbered keeps the exact
   text it was given (never renamed retroactively).
   *Where implemented:* `app/services/numbering.py`
   (`DocumentNumberFormat`, `format_document_number`),
   `app/routers/document_control.py`, migration `cc953b888c6b`.
   *Arises in:* Document Control, and every module that numbers a
   document (Contracts, Invoices, Bills, JV, POs, Quotations,
   Receipts, Payment Vouchers, Job Orders, Service Records).

15.2. **Staff photos on Support Monitoring.** **Status: DECIDED
   2026-09-11.** `User.photo` holds an optional staff photo (inline
   data URI, same pattern/size cap as `Company.logo`), uploaded from a
   staff member's own Staff Master page. Shown as a circular avatar on
   Support Monitoring and the Staff Master list; falls back to the
   person's initials when no photo is set. No requirement was given
   for cropping/aspect-ratio enforcement, so the raw uploaded image is
   shown `object-fit: cover` inside a circle -- revisit if a specific
   crop/aspect-ratio behaviour is wanted.
   *Where implemented:* `app/models/core.py` (`User.photo`),
   `app/services/monitoring.py`, migration `80a442a466b3`,
   `frontend/src/components/StaffAvatar.tsx`.
   *Arises in:* Staff Master, Support Monitoring.

## 16. Sample staff photos, bigger avatars, menu reordering (raised 2026-09-11)

16.1. **Sample photos are a generated icon, not a real photo --
   environment limitation, not a choice.** Asked for "real person" sample
   photos for the 8-staff demo; this environment's outbound network
   access is a small allowlist of code-library CDNs (confirmed by a
   403 testing a face-image host) and there is no image-generation
   tool available, so neither a real nor an AI-synthetic photo can be
   produced here. `avatar_photo_data_uri()` in `scripts/seed_demo.py`
   generates a flat-icon silhouette instead (pure stdlib PNG encoder,
   no dependency added), purely for sample/demo data -- the real
   feature (uploading an actual photo from Staff Master) is unaffected
   and already fully working. Revisit if a way to source real/
   synthetic photos becomes available.

16.2. **8 sample Company-1 staff.** **Status: DECIDED 2026-09-11.**
   5 more staff (Marcus, Farhana, Kevin, Siti, Bryan) added to
   `seed_demo.py` alongside the original 3 (Nico, Cherish, Wei Ling),
   purely so Support Monitoring has a realistic 8-person view to demo
   -- same roles/Group pattern as the original 3, no new business
   rule. Company 2 (Priya only) is untouched.

16.3. **Support Monitoring: bigger avatars, "Total Job Orders" tile
   removed.** **Status: DECIDED 2026-09-11.** Avatar size on the
   staff cards increased (30px -> 56px); the summary row now shows
   only Open Job Orders, Overdue, Unassigned, Pending Service Records
   and Un-Tested Software Tasks -- the redundant "Total Job Orders"
   tile (sum of open + resolved/closed) was dropped. The backend
   still computes and returns `total_job_orders`; only this screen
   stopped displaying it.

16.4. **Menu bar: choose the link sequence.** **Status: DECIDED
   2026-09-11.** Every link within a sidebar section (Operations /
   Accounts / Maintenance) can be dragged to reorder it -- a per-
   browser display preference (localStorage, one order list per
   section), same posture as the collapse state (#14.1's sibling
   feature): it changes where a link appears, never what a user can
   see (Group Authority-hidden links stay hidden regardless of
   position). Reordering across sections is not supported -- a link
   stays under the module area it belongs to.
   *Where implemented:* `frontend/src/components/NavSection.tsx`,
   `frontend/src/components/Layout.tsx`.
   *Arises in:* every module with a nav link.

---

## 17. Accounts menu default order + Tax/Currency/GL Types moved to Maintenance (raised 2026-09-11)

17.1. **Accounts section default order.** **Status: DECIDED 2026-09-11.**
   Set the default (pre-drag) order of the Accounts sidebar section to
   Dennis's requested sequence: Bank, Sales Quotation, Sales Invoice,
   Receipt Voucher, Accounts Payable, Payment Voucher, Journal Voucher,
   Chart of Accounts, GST and Account Period, Accounting Reports.
   Several existing links were relabeled to match the requested wording
   (Invoices -> Sales Invoice, Receipts -> Receipt Voucher, General
   Ledger -> Journal Voucher, Accounting Periods -> GST and Account
   Period, Bank Master File -> Bank) -- the underlying pages and routes
   are unchanged, only the nav label and position moved. This is still
   just a *default*: per #16.4 each user can drag-reorder their own
   copy, so this only sets what a fresh browser sees.

   Two items in the requested list have no dedicated page of their own,
   so they were mapped onto the closest existing route rather than
   adding a confusing duplicate nav entry -- flag for correction if
   either mapping is wrong:
   - **"Purchase Order"** -> `/accounts-payable`. Purchase Orders are
     already a section of the Accounts Payable page (alongside
     Suppliers and Bills), not a separate route -- a genuine standalone
     PO page/route was not built.
   - **"GST and Account Period"** -> `/accounting-periods` (relabeled).
     The GST F5-style return itself was NOT moved -- it stays a report
     under Accounting Reports (#48), since it's a report output, not a
     period-setup screen.

17.2. **GL Types, Tax Types, Currency Rate Table moved to Maintenance.**
   **Status: DECIDED 2026-09-11.** Per "Those tax type, currency type
   files should be in the Maintenance Section" -- moved out of the
   Accounts section into Maintenance, alongside Setup Lists (their
   closest sibling: all four are reference/master-data maintenance
   screens, not transactional). GL Types was moved along with Tax Types
   and Currency Rate Table even though only the latter two were named
   explicitly, since it's the same kind of reference-data screen and
   was the only one of the three left behind otherwise -- flag if GL
   Types was meant to stay under Accounts.
   *Where implemented:* `frontend/src/components/Layout.tsx`
   (`accountsItems` / `maintenanceItems` arrays). No route or page
   changes -- URLs are unchanged, only which sidebar section links to
   them.

---

## 18. Year-End Closing nav position; Job Orders Resolve/Close was a dead end (raised 2026-09-11)

18.1. **Year-End Closing moved to its own page/nav entry.** **Status:
   DECIDED 2026-09-11.** Per "Year End Closing shift below GST and
   Account Period" -- it used to be a card at the bottom of the
   Accounting Periods page; split out to its own route
   (`/year-end-closing`) and Accounts nav entry, positioned directly
   below "GST and Account Period". The Accounting Periods page now
   just points to it.
   *Where implemented:* `frontend/src/pages/YearEndClosingPage.tsx`
   (new), `frontend/src/pages/AccountingPeriodsPage.tsx` (trimmed),
   `frontend/src/components/Layout.tsx`, `frontend/src/App.tsx`.

18.2. **Job Orders could never actually be Resolved or Closed --
   fixed.** **Status: DECIDED 2026-09-11, flag if the assumptions
   below are wrong.** Requested as "Run through Job Orders and see
   what to touch up"; this is the finding, not a UI polish item. The
   `RESOLVED`/`CLOSED` statuses and the `resolved_at` column existed on
   the model from the very first build, and the Dashboard/Support
   Monitoring "open job orders" counts already excluded them (see
   `OPEN_STATUSES` in `app/services/monitoring.py`) -- but no endpoint
   ever set a Job Order to either status. Every Job Order was
   permanently stuck at Open or Assigned; the documented workflow
   (docs/workflows.md step 10: "Job Order is resolved and closed") was
   simply never wired up.

   Added `POST /job-orders/{id}/resolve` (Open/Assigned -> Resolved,
   stamps `resolved_at`), `.../close` (Resolved -> Closed), and
   `.../reopen` (undoes either, back to Assigned/Open -- owner-only,
   mirroring the Accounting Period reopen pattern, so a mistake never
   needs a direct database edit). Two defaults, not confirmed business
   rules -- flag if wrong:
   - **Who can resolve/close:** same access as the rest of this page
     (EDIT on service_operations, same as Assign/Due-date) -- no extra
     approval gate, since the workflow doc doesn't name a specific
     approver for this step the way it does for Excess Review (Nico/
     Cherish, SRV-004/011).
   - **No precondition check** (e.g. all Service Records must be
     Approved first) before allowing Resolve -- the workflow doc lists
     billing/invoicing as a prior step but doesn't say the system must
     enforce it before Resolve is allowed.
   *Where implemented:* `backend/app/routers/job_orders.py`,
   `backend/app/schemas/schemas.py` (`resolved_at` now returned),
   `frontend/src/pages/JobOrderDetailPage.tsx`,
   `frontend/src/lib/api.ts`. No migration needed -- the column already
   existed.

   **Superseded the same day -- see #19.1 below.** The explicit status
   list given afterwards ("open, closed, assigned, void") replaced this
   manual Resolve/Close pair with an auto-close rule; this entry is
   kept for history, not as the current design.

---

## 19. Job Order status rework, Service Record deduction workflow,
   Company/Individual relationships, Job Order printing (raised 2026-09-11)

19.1. **Job Order status: open/assigned/closed/void; auto-close
   replaces manual Resolve/Close.** **Status: DECIDED 2026-09-11.**
   RESOLVED is gone; VOID is new (a manual dead-end for a job that
   should never have been raised -- duplicate, raised in error --
   distinct from a normally finished job). A Job Order now auto-closes
   when its **most recently submitted** Service Record is both
   Approved and marked Completed ('C', not Uncompleted 'U') --
   `maybe_auto_close_job_order()` in
   `backend/app/services/service_records.py`. Only the latest record
   matters, so earlier Uncompleted visits don't block closing once the
   final visit is done and approved. Void requires a reason (audited);
   Reopen (owner-only, undoes either Closed or Void back to
   Assigned/Open) still exists for correcting a mistake without a
   direct database edit. Once Closed or Void, Assignment/Due-date/Log-
   a-Service-Record are hidden on the page and rejected server-side too
   (reopen first) -- a gap found while building this, not explicitly
   requested, but an obvious consequence of "finished/cancelled work
   shouldn't take new entries."
   *Migration:* `a025ca222e9c` rebuilds the `job_order_status` Postgres
   enum (no `DROP VALUE` exists) and renames `resolved_at` ->
   `closed_at`.

19.2. **Service Record: Completion (C/U), After-hours flag, and
   approver-keyed Deduction minutes.** **Status: DECIDED 2026-09-11.**
   `completion_status` is set by whoever submits the record (does this
   visit finish the job, or is another one needed) and drives 19.1's
   auto-close. `is_after_hours` is a manual tick (no office-hours/
   public-holiday calendar exists in this build to derive it from).
   `deducted_minutes` is a new field the approver keys in herself at
   approval time -- distinct from the objective `rounded_minutes` log
   -- confirmed via "actual is 240mins, deducted is 220mins or
   360mins." A new page, **Service Record Approval**
   (`/service-record-approval`, nav entry below Service Records),
   replaced the old one-click Approve button (which had no way to
   collect a minutes value) -- it prefills a *suggestion* per 19.3 but
   the approver can type any value.

19.3. **Urgent (x1.5) / After-hours-Weekend-Holiday (x2.0) deduction
   multiplier -- suggestion only, not enforced.** **Status: DECIDED
   2026-09-11.** `Job Order.is_urgent` is a manual tick (toggle on the
   Job Order detail page or at creation). The suggested deduction
   minutes on the Approval page is `rounded_minutes x` the higher of
   the two multipliers when both apply (confirmed: not stacked/
   multiplied together, so Urgent + after-hours suggests x2.0, not
   x3.0) -- `suggested_deduction_minutes()` in
   `backend/app/services/service_records.py`. This only changes what
   number is prefilled; the approver's typed-in value is what's
   actually deducted and posted, so getting the suggestion formula
   slightly wrong has no data-integrity consequence, only a
   convenience one. The multiplier does **not** touch the excess-hour
   billing rate (SRV-008's blended rate) -- flag if urgency/after-hours
   was meant to affect the dollar rate charged on excess time too, not
   just contract-hour-pool minutes consumed.

19.4. **Job Order printing.** **Status: DECIDED 2026-09-11.** The
   listing + filters this asked for already existed
   (`JobOrdersPage.tsx`); added the printing half -- a Print link per
   row and on the detail page, opening `/job-orders/:id/print`
   (`JobOrderPrintPage.tsx`), following the same pattern as every other
   printed document in the app (Quotation, Invoice, Receipt, Payment
   Voucher).

19.5. **Due date / Assignment shown side by side.** **Status: DECIDED
   2026-09-11.** Two small cards side by side on the Job Order detail
   page instead of stacked full-width -- pure layout, no field or
   behavior change.

19.6. **"Company / Individual" relationships -- rename + links, not a
   restructure.** **Status: DECIDED 2026-09-11 (confirmed scope: rename
   the label and add relationship links between existing records,
   *not* split Customer into two distinct entity types).** The
   Customers nav entry, page title, and table heading are relabeled
   "Company / Individual" -- the underlying `Customer` table/fields are
   unchanged (it already had `customer_type` = company/individual).
   New: `CustomerRelationship`, an undirected link from one Customer to
   another Customer **or** to a specific Contact at another company
   (covers all three levels asked for -- company-level and individual-
   level both use `to_customer_id`, since the level already follows
   from that Customer's own `customer_type`; company-contact-level uses
   `to_contact_id`; exactly one is set). `relationship_type` is free
   text (no fixed taxonomy was given, matching how `Customer.tags`
   already works) with a few suggested values in the UI. Undirected by
   default (one row, same label shown from either side) rather than a
   directional pair like "Parent of"/"Subsidiary of" -- a pragmatic
   default, flag if a directional model was actually wanted. "Can be
   customer or supplier or dealer" is noted as page copy, not built as
   a merge with the separate Supplier entity (Accounts Payable) --
   that's a materially bigger change and wasn't the confirmed scope.
   Every other screen that references "Customer" (Job Orders,
   Contracts, Invoices, etc.) keeps that wording -- only the Customers
   module's own nav/page labels changed, to keep this a bounded rename
   rather than an app-wide sweep.
   *Where implemented:* `backend/app/models/customers.py`
   (`CustomerRelationship`), `backend/app/routers/customers.py`,
   `backend/app/schemas/schemas.py`, `frontend/src/pages/
   CustomerDetailPage.tsx`, `frontend/src/pages/CustomersPage.tsx`,
   `frontend/src/components/Layout.tsx`. Migration: `c2b41b06fd17`.

19.7. **Incident Module -- deferred.** Requested ("log calls, route to
   Sales Quotation / Job Order / Software Tasks / a callback, future
   Outlook integration") but explicitly deferred to its own follow-up
   pass per Dennis's instruction ("settle company/individual first
   then new incident module later"). Confirmed so far: converting an
   Incident should auto-create the real linked record (not just route/
   assign) -- to be designed in full when that pass starts. Logged
   alongside the Support Staff Mobile App (see
   [docs/planned-work.md](docs/planned-work.md)) as confirmed-but-not-
   yet-built work.

---

## 20. Ops Dashboard: personal task tracker per staff member (raised 2026-09-11)

Requested as "Create a staff individual ops dashboard based on the
staff login," modeled on a sample screenshot (categories of tasks, a
status/next-action/owner/due/follow-up table, stat tiles, a status
legend, filters, expand/collapse, export).

20.1. **Both freeform tasks AND a real-ERP-data rollup, confirmed
   2026-09-11.** Two distinct sections on one page, not merged into one
   data model:
   - Freeform: `OpsTaskCategory`/`OpsTask` -- manually created
     categories and tasks, independent of Job Orders/Contracts, with
     the exact columns in the sample (status, next action, owner
     label, due label, follow-up staff, follow-up date). `owner_label`
     and `due_label` are free text, not foreign keys/real dates --
     the sample itself mixes values like "Dennis + Bot" and "Month-end"
     with real names/dates in those columns, so a strict type would
     reject exactly what the sample shows.
   - Real-ERP rollup: read-only "My open Job Orders" and "My Software
     Tasks" sections, computed by filtering existing tables
     (`JobOrder.assigned_to_user_id`, `SoftwareTask.assigned_programmer_id`
     /`tester_user_id`) for the viewed staff member -- no new model.

20.2. **Visibility: everyone sees their own; Owner/Service
   Lead/Sales Manager can also view AND edit anyone's, confirmed
   2026-09-11.** Mirrors the "manager-ish" role set already used for
   Service Record approval and Excess Review (`MANAGER_ROLES` in
   `app/routers/ops_dashboard.py`) rather than inventing a new role
   concept. A manager gets a "Viewing" dropdown to switch to any staff
   member's dashboard; anyone else sees no such control.

20.3. **No in-app "Reset seed" button.** The sample screenshot has one,
   but it's a real feature now, not a demo tool -- a button that wipes
   a staff member's actual task list would contradict "never
   permanently delete important business or financial records" in
   spirit (these aren't financial records, but the same caution
   applies). Sample/demo content instead comes from `seed_demo.py`
   like every other module's demo data, flagged `is_sample=True` and
   shown with a "(sample)" label.

20.4. **"Edit staff list" links to Staff Master instead of a new admin
   screen.** Staff Master already is the canonical place to manage
   staff accounts; duplicating that here would just be two places that
   can drift out of sync. The button in the sample is treated as
   "manage who can appear in the follow-up-staff dropdown," which is
   exactly what Staff Master already does.

20.5. **Export JSON** downloads the currently-loaded dashboard (all
   categories/tasks/rollups for whoever is being viewed) as a `.json`
   file, client-side -- no backend export endpoint, since there's
   nothing to compute beyond what's already fetched.

*Where implemented:* `backend/app/models/ops_tasks.py`,
`backend/app/routers/ops_dashboard.py`, `backend/app/schemas/schemas.py`,
`frontend/src/pages/OpsDashboardPage.tsx`, nav entry ("My Ops
Dashboard") in `frontend/src/components/Layout.tsx`, module key
`ops_dashboard` in Module Control/Group Authority (all four default
Groups get FULL). Migration: `08ceed0e5b5d`.

---

## How to use this document

- Do not start detailed schema or workflow design for an area until the
  decisions that affect it are resolved, or an explicit interim
  assumption is agreed with Dennis and recorded here.
- When a decision is made, update the relevant item's status (e.g. to
  **DECIDED — <summary>**, with a pointer to where the rule is documented
  in [business-requirements.md](business-requirements.md) or a future
  module-specific requirements document) rather than deleting it, so the
  decision history is preserved.
- New items should be added here as detailed requirements gathering
  uncovers further undecided rules — this list is a living document, not
  a one-time checklist.
