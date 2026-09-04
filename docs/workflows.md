# Major Business Workflows

Status: **proposed / conceptual**. These are proposed end-to-end workflows
across the modules described in [module-map.md](module-map.md), based on
current documentation. They describe the expected *shape* of each process
so that architecture and detailed requirements can be planned — they are
**not** confirmed business rules.

Wherever a step depends on a business rule that has not been provided,
this document flags it and points to
[open-business-decisions.md](open-business-decisions.md) rather than
assuming an answer.

---

## A. Lead → Opportunity → Quotation → Sales Order

**Trigger**
A new lead is captured (e.g. inbound enquiry, referral, outbound
prospecting).

**Steps**
1. Lead is captured and recorded in CRM.
2. Lead is qualified; if valid, converted into an Opportunity with an
   estimated value and stage.
3. Opportunity progresses through pipeline stages as sales activity
   continues (calls, meetings — tracked in CRM).
4. Sales prepares a Quotation (in Sales) from the opportunity, including
   products/services/hardware and pricing.
5. Quotation is sent to the customer for review; revisions may occur.
6. Customer accepts the quotation.
7. Quotation is converted into a confirmed Sales Order.
8. Sales Order is handed off to the relevant fulfilment path: Service
   Contracts (if a contract was sold), Projects (if a project was sold),
   and/or Hardware Management (if hardware was sold).

**Responsible user/department**
Sales team (CRM and Sales modules); sales management for oversight.

**Data created**
Lead record, Opportunity record, Quotation and quotation lines, Sales
Order and sales order lines, activity/interaction history.

**Approval points**
- Quotation approval before sending to customer — **whether an internal
  approval step exists, and for what discount/value thresholds, is not
  yet decided.**
- Sales Order confirmation — likely requires explicit customer acceptance,
  but the confirmation mechanism (signed quote, PO from customer, verbal)
  is not yet decided.

**Financial impact**
No financial posting at Lead/Opportunity stage. A Quotation is not yet a
financial commitment. A confirmed Sales Order creates the basis for future
revenue (via Billing) but is not itself a financial transaction until
invoiced.

**Possible exceptions**
- Opportunity lost/abandoned before quotation.
- Quotation rejected or expires without acceptance.
- Partial acceptance (customer accepts some lines, not all).
- Sales order later amended or cancelled after confirmation.

**Automation opportunities**
- Auto-reminders for stale opportunities/quotations.
- Auto-numbering and templated quotation documents.
- Automatic handoff notification to Service Contracts/Projects/Hardware
  Management when a sales order is confirmed.

---

## B. New Customer → Contract → Service Setup

**Trigger**
A confirmed Sales Order includes a service contract (from Workflow A), or
an existing customer purchases a new contract directly.

**Steps**
1. If the customer is new, a Customer Management record (and contacts/
   sites) is created or confirmed.
2. A Service Contract is created from the sales order, with contract
   lines defining scope, included hours/quantity, and SLA terms.
3. Contract is activated (start date, initial status).
4. Service setup activities occur as needed (e.g. onboarding tasks,
   initial hardware installation via Workflow G, access provisioning) —
   the extent of "service setup" as a formal step is not yet defined.
5. Contract becomes the reference point for Helpdesk entitlement checks
   and recurring Billing.

**Responsible user/department**
Sales (contract creation from order), contract administration/service
operations (setup), Customer Management owner (customer record).

**Data created**
Customer record (if new), Contract and contract lines, contract activation
record, service setup/onboarding records (if tracked).

**Approval points**
- Contract terms approval before activation (who signs off on
  non-standard terms is not yet decided).
- Customer credit check before contract activation — **whether a credit
  check/limit process exists is not yet decided.**

**Financial impact**
No immediate revenue recognition at contract creation; recurring billing
(Workflow under Billing) will draw on the contract once active. Contract
value may be used for forecasting/reporting.

**Possible exceptions**
- Contract creation without a prior sales order (e.g. manually entered).
- Customer onboarding delays contract activation.
- Contract terms renegotiated before or shortly after activation.

**Automation opportunities**
- Auto-creation of a draft contract from an accepted quotation/sales
  order.
- Checklist/task automation for standard service setup steps.
- Notification to Billing when a contract becomes active, to schedule
  recurring billing.

---

## C. Customer Issue → Helpdesk Ticket → Staff Assignment → Timesheet → Contract Hour Deduction → Billing

**Trigger**
A customer reports an issue or service request.

**Steps**
1. Ticket is logged in Helpdesk / Service Operations, linked to the
   customer (and asset, if applicable via Hardware Management).
2. Ticket is categorized/prioritized; SLA timers start based on the
   customer's Service Contract.
3. Ticket is assigned to a staff member (or escalated).
4. Staff performs the work and logs time via Timesheets against the
   ticket.
5. Logged time is classified as contract-covered, billable (beyond
   contract), or non-billable — **the classification rule is not yet
   decided.**
6. If contract-covered, the Service Contract's remaining hours/quantity
   are reduced by the logged time — **the exact deduction rule (e.g.
   rounding, minimum increments) is not yet decided.**
7. If billable beyond contract entitlement, the time flows to Billing as
   a billable line.
8. Ticket is resolved and closed.

**Responsible user/department**
Service/support staff (ticket handling, time logging); service operations
management (assignment/escalation, SLA oversight); finance/billing team
(billing step).

**Data created**
Helpdesk ticket, assignment/escalation history, timesheet entries, contract
consumption records, (conditionally) billable line items for Billing.

**Approval points**
- Timesheet approval before it affects contract hours or billing (manager
  approval expected, but the approver and threshold are not yet decided).
- Approval for billing work that exceeds contract entitlement — **whether
  customer sign-off is required before billing overage is not yet
  decided.**

**Financial impact**
No direct financial posting from the ticket itself. Financial impact
occurs when billable time (beyond contract) is invoiced via Billing, or
indirectly through contract cost-to-serve tracking (if used for
profitability reporting — not yet decided).

**Possible exceptions**
- Ticket exceeds SLA (breach handling not yet decided).
- Ticket requires more hours than remain on the contract — **what happens
  when contract hours are exhausted (pause work, auto-bill overage,
  require approval) is not yet decided; see
  [open-business-decisions.md](open-business-decisions.md).**
- Ticket reassigned multiple times.
- Work performed is later disputed by the customer.

**Automation opportunities**
- Auto-assignment based on staff availability/skill.
- SLA breach alerts.
- Automatic contract-hour deduction from approved timesheets.
- Automatic flagging of tickets nearing contract hour exhaustion.

---

## D. Project → Tasks → Timesheet → Cost → Revenue → Billing

**Trigger**
A Sales Order for project-based work is confirmed, or a project is set up
directly for an existing engagement.

**Steps**
1. Project is created in Projects, with scope, budget, and timeline.
2. Project is broken into tasks/milestones and assigned to staff.
3. Staff log time against project tasks via Timesheets.
4. Logged (approved) time contributes to project cost tracking (labour
   cost) — cost rate source (e.g. standard cost per role) is not yet
   decided.
5. Project revenue is recognized according to the project's billing
   method (time-and-materials vs. fixed price/milestone) — **which
   billing method(s) apply, and how, is not yet decided.**
6. Billing generates invoices from project billing events (time-based
   lines or milestone completion).

**Responsible user/department**
Project managers (setup, task assignment, progress tracking); project
staff (time logging); finance/billing team (billing step).

**Data created**
Project record, tasks/milestones, timesheet entries, project cost
accumulation, billing events/lines.

**Approval points**
- Timesheet approval (as in Workflow C).
- Milestone completion sign-off (for milestone billing) — approver not
  yet decided.
- Project budget overrun approval — **whether/when a project needs
  re-approval if it exceeds budget is not yet decided.**

**Financial impact**
Project cost accrues as time is logged; revenue is recognized when billed
(and potentially before, if accrual-based revenue recognition is used —
not yet decided). Both cost and revenue feed Finance / Accounting and
project profitability reporting.

**Possible exceptions**
- Project runs over budget or over timeline.
- Project paused or cancelled mid-way.
- Scope change requiring a contract/quotation amendment.

**Automation opportunities**
- Budget-vs-actual alerts as timesheets are logged.
- Automatic draft invoice generation on milestone completion or at the
  end of a billing period for time-and-materials work.
- Project status dashboards (Reporting).

---

## E. Sales → Commission Calculation → Commission Approval → Payment

**Trigger**
A sale is confirmed (Sales Order) and/or invoiced/paid, depending on when
commission is deemed earned (not yet decided).

**Steps**
1. Sales data (order and/or invoice and/or payment, depending on the
   trigger point decided) becomes eligible for commission calculation.
2. Commission Management calculates the commission amount owed to the
   relevant salesperson(s) — **the calculation formula (e.g. flat
   percentage, tiered, product-specific rates, split commissions) is not
   yet decided.**
3. Calculated commission is submitted for approval.
4. Approver reviews and approves (or rejects/adjusts) the commission.
5. Approved commission becomes payable and is scheduled for payment —
   **the payment mechanism (e.g. via payroll, via Accounts Payable-style
   payout) is not yet decided.**
6. Payment is recorded.

**Responsible user/department**
Sales management (visibility), finance (calculation/administration),
designated approver (approval), HR/payroll (payment execution, if
applicable — not yet scoped as a module).

**Data created**
Commission calculation records, approval history, commission payment
records.

**Approval points**
- Commission approval before payment — **approver role, and whether
  multi-level approval is required for large amounts, is not yet
  decided.**

**Financial impact**
Commission is an expense/payable for the company once approved. It
affects sales cost-of-sale/profitability reporting and, once paid,
reduces cash.

**Possible exceptions**
- Sale is later cancelled or refunded after commission was calculated or
  paid — **clawback rule is not yet decided.**
- Split commission across multiple salespeople.
- Disputed commission amount.

**Automation opportunities**
- Automatic commission calculation on the decided trigger event.
- Automatic routing for approval with configurable thresholds.
- Commission statements/reporting for sales staff.

---

## F. Purchase → Purchase Order → Goods Receipt → Supplier Invoice → Payment

**Trigger**
A need to purchase goods or services is identified (e.g. stock reorder,
hardware needed for a confirmed sale, general procurement need).

**Steps**
1. Purchase requisition/request is raised in Purchasing.
2. Purchase Order is created and sent to the supplier — **approval
   threshold(s) before a PO can be sent are not yet decided.**
3. Goods (or services) are received; Goods Receipt is recorded in
   Purchasing, updating Inventory (and Hardware Management, for
   serialized hardware).
4. Supplier sends an invoice; it is recorded in Accounts Payable and
   matched against the PO and goods receipt (2-way/3-way matching — not
   yet decided which is required).
5. Supplier invoice is approved for payment — **approval rule not yet
   decided.**
6. Payment to the supplier is scheduled and recorded.

**Responsible user/department**
Procurement/purchasing staff (requisition, PO); warehouse/hardware staff
(goods receipt); finance/accounts team (invoice matching, approval,
payment).

**Data created**
Purchase requisition, Purchase Order and lines, Goods Receipt records,
Supplier Invoice, payment records, updated Inventory/Hardware Management
records.

**Approval points**
- PO approval before sending to supplier.
- Supplier invoice approval before payment, including handling of
  mismatches between PO, receipt, and invoice (rule not yet decided).

**Financial impact**
A liability (Accounts Payable) is created when the supplier invoice is
recorded; cash decreases when payment is made. Goods receipt may also
affect inventory valuation (valuation method not yet decided).

**Possible exceptions**
- Partial delivery / partial goods receipt.
- Invoice amount does not match PO/receipt (price or quantity
  discrepancy).
- Damaged/rejected goods on receipt.
- Supplier invoice received before goods, or vice versa.

**Automation opportunities**
- Auto-reorder suggestions from Inventory stock levels.
- Automated 2-way/3-way match checking with exception flagging.
- Payment run scheduling based on supplier terms.

---

## G. Hardware Purchase → Inventory → Delivery → Customer Installation → Asset/Serial Number

**Trigger**
Hardware is purchased (via Workflow F) for stock or for a specific
confirmed customer sale.

**Steps**
1. Hardware is received via Goods Receipt (Purchasing) and enters
   Inventory as stock.
2. For serialized hardware, individual units are registered as assets in
   Hardware Management with serial/asset numbers, linked to the goods
   receipt.
3. When sold (Sales Order), the relevant asset(s) are allocated to the
   order and linked to the customer.
4. Hardware is delivered to the customer site (Customer Management
   provides the site/address).
5. Hardware is installed; installation is recorded against the asset,
   including installation date and location.
6. Asset status is updated to "installed" and linked to the customer's
   Service Contract, if the asset is covered by one.

**Responsible user/department**
Warehouse/hardware team (receipt, asset registration, delivery); field
engineers (installation); sales/customer management (customer/site
linkage).

**Data created**
Inventory stock movement records, Hardware asset records (serial-tracked),
delivery records, installation records, asset-to-customer/site/contract
links.

**Approval points**
- None obviously required by default, but **whether installation requires
  customer sign-off/acceptance is not yet decided.**

**Financial impact**
Inventory value moves from stock to cost-of-goods-sold upon
delivery/installation (exact timing and valuation method not yet
decided). Hardware sale revenue is recognized through Billing, typically
at delivery or installation (not yet decided).

**Possible exceptions**
- Hardware fails on installation and must be replaced (RMA process not
  yet decided).
- Delivery delayed or partial (multi-unit orders).
- Asset later relocated to a different customer/site.
- Asset returned/decommissioned.

**Automation opportunities**
- Auto-generation of an asset record from goods receipt for serialized
  items.
- Delivery/installation scheduling and notifications.
- Warranty expiry reminders.

---

## H. Invoice → Payment → Reconciliation → Outstanding Balance

**Trigger**
An invoice is issued to a customer (from Billing, arising from any of
Workflows A–G that result in billable activity).

**Steps**
1. Invoice is issued (and, in future, submitted via InvoiceNow/Peppol —
   see Integrations).
2. Invoice is recorded as an open receivable in Accounts Receivable.
3. Customer makes a payment (in full or in part).
4. Payment is recorded and allocated against the invoice(s) — **the
   allocation rule when a payment doesn't exactly match an invoice
   amount, or covers multiple invoices, is not yet decided.**
5. Payment is reconciled against bank records (manually or via future
   banking integration).
6. Outstanding balance (if any) is tracked and aged for follow-up.

**Responsible user/department**
Finance/accounts team.

**Data created**
Payment records, payment allocations, reconciliation records, AR aging
data.

**Approval points**
- Write-off of a small unreconciled difference or bad debt — **approval
  rule not yet decided.**
- Credit note issuance if the invoice needs correction — **approval rule
  not yet decided (see also Workflow Billing in
  [module-map.md](module-map.md)).**

**Financial impact**
Direct: reduces the customer's outstanding balance and increases recorded
cash on payment; feeds Finance / Accounting for cash position and revenue
reporting.

**Possible exceptions**
- Overpayment or underpayment by the customer.
- Payment received with no clear invoice reference.
- Disputed invoice held while resolution is pending.
- Bad debt / non-payment beyond a threshold.

**Automation opportunities**
- Automated payment matching (e.g. by reference number/amount).
- Automated aging reports and overdue reminders.
- Bank feed integration for reconciliation (future, via Integrations).

---

## I. Contract Expiry → Renewal Opportunity → Renewal Quotation → New Contract

**Trigger**
A Service Contract approaches its expiry date (lead time not yet decided).

**Steps**
1. Approaching expiry is detected (based on contract end date) and a
   renewal Opportunity is created/flagged in CRM.
2. Sales reviews the account (usage, satisfaction, any issues) ahead of
   renewal discussion — **what information must be reviewed before
   renewal is not yet decided.**
3. A renewal Quotation is prepared in Sales (may repeat prior terms or
   propose changes).
4. Customer accepts the renewal quotation.
5. A new (or amended/extended) Service Contract is created/activated,
   effective from the prior contract's expiry — **whether renewal creates
   a new contract record or extends the existing one is not yet
   decided.**
6. Prior contract is closed out; any unused hours from the old contract
   are handled — **whether unused hours expire, roll over, or are
   forfeited is not yet decided (see
   [open-business-decisions.md](open-business-decisions.md)).**

**Responsible user/department**
Sales (renewal opportunity and quotation); contract administration
(contract closeout/activation); Customer Management (account status).

**Data created**
Renewal Opportunity, renewal Quotation, new/amended Contract record,
contract closeout record.

**Approval points**
- Renewal terms approval, especially if pricing changes materially — not
  yet decided.

**Financial impact**
No immediate financial transaction at expiry; the renewed contract
resumes recurring billing (Billing) once active. A lapse between expiry
and renewal (if any) may create a service gap — handling not yet decided.

**Possible exceptions**
- Customer does not renew (churn) — contract lapses; **what happens to
  outstanding contract hours or open tickets is not yet decided.**
- Renewal negotiated with materially different terms.
- Renewal delayed past the expiry date, creating a gap in coverage.

**Automation opportunities**
- Automated renewal reminders at configurable lead times before expiry.
- Auto-drafting a renewal quotation from the expiring contract's terms.
- Dashboard of upcoming contract expiries (Reporting).
