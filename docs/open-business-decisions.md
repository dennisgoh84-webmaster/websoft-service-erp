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

Status legend: all items are **OPEN** (undecided) unless noted otherwise.

---

## 1. Service Contracts & Hours

1.1. **How do service contracts calculate consumed hours?**
   e.g. actual time logged, rounded to a minimum increment, per-ticket
   minimum charge, etc.
   *Arises in:* Service Contracts, Timesheets; Workflow C.

1.2. **Do unused contract hours expire, roll over, or get forfeited** at
   the end of a contract period, and if they roll over, is there a cap?
   *Arises in:* Service Contracts; Workflow I.

1.3. **What happens when contract hours are exhausted mid-contract?**
   Options might include pausing further work, requiring customer
   approval to continue, or automatically billing overage — but the
   choice is Webmaster's.
   *Arises in:* Service Contracts, Helpdesk / Service Operations, Billing;
   Workflow C.

1.4. **How is support/work beyond contract entitlement billed?**
   Rate basis, minimum billing increments, and whether customer
   pre-approval is required before billing overage.
   *Arises in:* Billing, Helpdesk / Service Operations; Workflow C.

1.5. **What SLA terms apply, and how are SLA breaches handled?**
   (e.g. penalties, escalation, reporting.)
   *Arises in:* Service Contracts, Helpdesk / Service Operations;
   Workflow C.

1.6. **Does contract renewal create a new contract record or extend the
   existing one**, and how is a coverage gap (if renewal is late) handled?
   *Arises in:* Service Contracts; Workflow I.

1.7. **Is a customer credit check or credit limit required before
   activating a new contract?**
   *Arises in:* Service Contracts, Customer Management; Workflow B.

## 2. Billing & Invoicing

2.1. **What is the recurring billing cycle for contracts** (e.g. monthly
   in advance, monthly in arrears, quarterly, annual)? Can it vary by
   customer/contract?
   *Arises in:* Billing, Service Contracts.

2.2. **What invoice approval rules apply** before an invoice is issued to
   a customer (e.g. value thresholds, who approves)?
   *Arises in:* Billing.

2.3. **What is the credit note approval process** (who can approve, at
   what value)?
   *Arises in:* Billing.

2.4. **What billing method applies to projects** — time-and-materials,
   fixed price/milestone billing, or a mix, and how is this decided per
   project?
   *Arises in:* Billing, Projects; Workflow D.

2.5. **When is revenue recognized** for contracts, projects, and hardware
   sales (e.g. on invoice, on delivery/installation, over the contract
   period)?
   *Arises in:* Billing, Finance / Accounting; Workflows B, D, G.

2.6. **How are quotations internally approved** before being sent to a
   customer (e.g. discount thresholds requiring management sign-off)?
   *Arises in:* Sales; Workflow A.

## 3. Payments & Accounts Receivable

3.1. **How are customer payments allocated** when a payment does not
   exactly match one invoice, or covers multiple invoices?
   *Arises in:* Accounts Receivable; Workflow H.

3.2. **What is the write-off / bad debt process** for small unreconciled
   differences or uncollectable balances, and who approves it?
   *Arises in:* Accounts Receivable; Workflow H.

3.3. **What happens to an invoice under dispute** (e.g. hold collections,
   partial payment handling)?
   *Arises in:* Accounts Receivable, Billing; Workflow H.

## 4. Purchasing & Accounts Payable

4.1. **What purchase order approval thresholds apply** (e.g. value-based
   approval levels)?
   *Arises in:* Purchasing; Workflow F.

4.2. **Is 2-way or 3-way matching required** for supplier invoices
   (PO vs. receipt vs. invoice), and how are mismatches handled?
   *Arises in:* Accounts Payable, Purchasing; Workflow F.

4.3. **What is the supplier invoice approval process** before payment is
   released?
   *Arises in:* Accounts Payable; Workflow F.

## 5. Inventory & Hardware

5.1. **What stock adjustment rules apply** (who can adjust stock, what
   approval/reason-code is required for discrepancies)?
   *Arises in:* Inventory.

5.2. **What inventory valuation method is used** (e.g. FIFO, weighted
   average, standard cost)?
   *Arises in:* Inventory, Finance / Accounting; Workflow G.

5.3. **Does hardware installation require customer sign-off/acceptance**
   before it is considered complete (and billable)?
   *Arises in:* Hardware Management; Workflow G.

5.4. **What is the RMA / hardware failure and replacement process**?
   *Arises in:* Hardware Management, Inventory; Workflow G.

5.5. **What warranty terms apply to hardware**, and how are they tracked
   and enforced?
   *Arises in:* Hardware Management; Workflow G.

## 6. Commission Management

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
   *Arises in:* Projects, Timesheets, Finance / Accounting; Workflow D.

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

8.3. **How is service ownership defined** for ongoing contracts/tickets
   (e.g. a named account engineer vs. a shared team queue)?
   *Arises in:* Service Contracts, Helpdesk / Service Operations.

8.4. **What are the detailed user roles and permission levels** across the
   system (beyond "authentication and RBAC are required")? e.g. what can a
   support engineer see/edit vs. a finance user vs. a manager.
   *Arises in:* Core / Administration — this affects every module.

## 9. Timesheets & Approval

9.1. **Who approves submitted timesheets**, and within what time frame
   (e.g. weekly approval by a direct manager)?
   *Arises in:* Timesheets; Workflows C, D.

9.2. **How is time classified as billable, non-billable, or
   contract-covered**, and can staff choose, or is it determined by the
   ticket/project/contract context automatically?
   *Arises in:* Timesheets, Helpdesk / Service Operations, Projects,
   Service Contracts; Workflow C.

## 10. Data & Scope (carried over from business requirements)

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
