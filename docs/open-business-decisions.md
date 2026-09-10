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
   *Arises in:* Billing.

## 3. Payments & Accounts Receivable

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
   *Arises in:* Purchasing.

4.5. **How are PO/invoice matching mismatches handled** under the PUR-002
   2-way match (e.g. price or quantity discrepancy)?
   *Arises in:* Accounts Payable, Purchasing; Workflow F.

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
