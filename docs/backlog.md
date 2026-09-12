# Backlog

A short, checkable list of what's pending, so we can just work down it.
Full detail for each item lives in [planned-work.md](planned-work.md) or
[open-business-decisions.md](open-business-decisions.md) -- linked per
item below rather than repeated here. Tick an item off when it's built
(or move it, with a short note, if it turns out to need more decisions
first) -- don't delete finished lines, so this stays a record of what
shipped and when.

## Waiting on Dennis to pick up (deferred 2026-09-12)

- [ ] **GL Transactions / multi-currency** -- GL debit/credit ledger
  view, default ledger codes per document header/line, and original +
  base (SGD) currency amounts on AR/AP/JV. The largest item here.
- [ ] **Bank Portal / ZSOFT HP Agency** -- still needs Dennis to say
  what this actually is (an in-app record + Send button, vs. literal
  automation of a real bank's website) before it can be started safely.

## Confirmed scope, not yet built

- [x] **Mobile web app for Support Staff** -- built 2026-09-12. Time
  in/out, work description, camera photo/video attachments, finger-drawn
  signature + watermarked chop photo sign-off. All 8 open questions
  settled. Route: `/mobile`.
  → [planned-work.md #1](planned-work.md#1-mobile-web-app-for-support-staff----on-site-job-order--service-record-capture-raised-2026-09-11-built-2026-09-12)
- [x] **Incident Module** -- built 2026-09-12. In-app screen (log,
  route to Quotation/Job Order/Software Task, or a callback status) is
  live; the Outlook Add-in half is scaffolded only -- not deployable/
  testable without a real Microsoft 365 tenant + HTTPS host (see
  outlook-addin/README.md).
  → [planned-work.md #2](planned-work.md#2-incident-module----support-staff-callissue-log-with-routing-to-salesjob-ordersoftware-tasks-raised-2026-09-11-deferred-until-after-companyindividual)
- [ ] **eSignature + eDocument attachments** -- across every document
  type, one pass at the end rather than per-document.
  → [planned-work.md #3](planned-work.md#3-esignature--edocument-attachments----all-operations-and-accounting-documents-raised-2026-09-12-put-on-the-waiting-list-at-the-end-then-we-build-it-in)
- [ ] **eApproval Master** -- generic, authority-based, multi-staff,
  value-gated approval framework; would eventually absorb the one-off
  Service Record approval logic.
  → [planned-work.md #4](planned-work.md#4-eapproval-master----authority-based-value-gated-multi-staff-approvals-across-documents-raised-2026-09-12)
- [ ] **Product "Is Stock" flag / Stock Master** -- blocked on the
  separate Websoft Stock Distribution ERP project existing first.
  → [planned-work.md #5](planned-work.md#5-product-is-stock-flag--stock-master-item-selection----pending-websoft-stock-distribution-erp-raised-2026-09-12)
- [ ] **Odoo migration program** -- Contacts/Subscriptions/Timesheets/
  Quotations/Invoices/Receipts/Chart of Accounts. 6 open questions on
  access method, field mapping, cutover sequencing.
  → [planned-work.md #6](planned-work.md#6-odoo-migration-program----contacts-subscriptions-timesheets-sales-quotationsinvoicesreceipts-chart-of-accounts-raised-2026-09-12)
- [ ] **WhatsApp OTP** as a second login factor -- blocked on
  provisioning a WhatsApp Business API account (Twilio/Meta); email OTP
  already works today.
  → [planned-work.md #7](planned-work.md#7-whatsapp-otp-as-a-second-login-factor-raised-2026-09-12-deferred)

## Partially open

- [ ] **Commission Management** -- the GP-based report is built;
  approval workflow, clawback rules, and payout mechanism (6.3-6.5) are
  still fully open.
  → [open-business-decisions.md #6](open-business-decisions.md#6-commission-management)
- [ ] Smaller longstanding open questions not currently blocking
  anything in progress (Projects budget-overrun process, detailed
  role/permission matrix, sales/service ownership definitions, etc.).
  → [open-business-decisions.md #7-8](open-business-decisions.md#7-projects)

---
Last updated: 2026-09-12
