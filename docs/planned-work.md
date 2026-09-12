# Planned Work

Confirmed future work that has been described in enough detail to record,
but is **not yet designed or built** -- distinct from
[open-business-decisions.md](open-business-decisions.md) (undecided items
blocking something already in progress) and
[business-requirements.md](business-requirements.md) (requirements for
areas actively being built). An item here moves to those documents (and to
actual implementation) once its turn comes.

---

## 1. Mobile web app for Support Staff -- on-site Job Order / Service Record capture (raised 2026-09-11, targeted for next week)

Requested as: a small mobile web login for Support Staff, separate from
the main desktop app, to work on-site against Job Orders and Service
Records.

**Confirmed scope, as given:**

- A **mobile web login** for Support Staff (not a native app) -- presumably
  reuses the existing user accounts/auth, scoped down to a mobile-friendly
  view of just Job Orders and Service Records.
- **Time in / time out** capture for a Service Record, on-site.
- Recording **what work was done** (a description/outcome of the visit).
- Attaching **photos or videos** to a Service Record.
- A **company-chop sign-off process** for each completed Service Record:
  1. At completion, Support Staff presents the Service Record details to
     the customer's in-charge person on-site.
  2. That person signs and states their name (a signature + printed name
     capture).
  3. The customer then stamps ("chops") a physical piece of paper with
     the company chop.
  4. Support Staff photographs that chop.
  5. The system stores the chop photo and **overlays it beside the staff
     signature**, keeping both together with the Service Record PDF.
  6. This whole sequence repeats for **every** Service Record -- it is not
     a one-time-per-customer or one-time-per-contract capture.
- **Chop photos must not be re-usable.** Explicitly called out as the
  most important issue. Read as: a chop photo captured for one Service
  Record must not be attachable to, or reappear on, a different Service
  Record -- almost certainly to prevent a photo of a genuine chop being
  reused to fake sign-off on unrelated/future visits.

**Open questions this will need answered before design starts** (per
CLAUDE.md's "never assume a business rule when requirements have not been
provided" -- not resolved here, just flagged so they're ready to ask):

1. **Auth model** -- do Support Staff log in with their existing
   User/Group Authority account (just via a mobile-optimized screen), or
   is this a separate, more restricted credential/role? What should a
   Support Engineer be able to see/do here versus in the desktop app --
   same Group Authority module permissions, or a deliberately narrower
   mobile-specific scope (e.g. only their own assigned Job Orders)?
2. **Time in/out vs. existing "minutes worked"** -- Service Records today
   record a single `raw_minutes` duration, entered after the fact. Does
   time-in/time-out on mobile *replace* that (minutes computed from the
   two timestamps), or sit alongside it? What happens if a visit spans a
   time-in with no matching time-out (staff forgot, connectivity lost)?
3. **"What is done" field** -- a required structured field, a free-text
   note, or both? Does it replace or supplement the existing Job
   Order/Service Record data already captured (subject, outcome,
   completion status)?
4. **Photo/video attachments** -- any limit on count, size, or format?
   Are they attached to the Service Record generally, or specifically
   tied to proving the work (e.g. before/after photos)? Storage approach
   (this app currently inlines small images as base64 data URIs for
   logos/avatars -- video and multiple photos per visit are a different
   scale and likely need real file/object storage, not that pattern).
5. **Signature capture** -- drawn on-screen (finger/stylus) or typed
   name only, per the request's wording ("signing and stating his/her
   Name")? Is the customer in-charge person expected to be an existing
   Contact record on that Company/Individual, or can any name be typed
   free-text on the spot?
6. **"Not allow re-use" -- how is this enforced?** Candidate approaches:
   perceptual/exact image-hash comparison against every previously
   stored chop photo (reject a duplicate at upload time), binding the
   capture to a single-use session/token tied to that specific Service
   Record so an already-used image can't be re-submitted elsewhere,
   device camera capture only (no upload-from-gallery, to stop reusing
   an old photo), embedding a visible/invisible per-Service-Record
   watermark or timestamp overlay at capture time, or some combination.
   This is flagged as the single most important part of the request and
   will need a concrete decision before it can be built.
7. **Storage and retention** -- chop photos and signatures become part of
   the permanent record per this project's audit-trail rules (never
   permanently delete). Confirm they're retained for as long as the
   Service Record / Job Order itself, with the same soft-delete posture
   as everything else.
8. **Offline / connectivity** -- Support Staff are on-site, possibly with
   poor connectivity. Does the mobile app need offline capture with
   later sync, or is a live connection assumed?

**Not yet started.** No models, routes, or UI exist for this. Recorded
here so it isn't lost before next week's work begins.

---

## 2. Incident Module -- Support Staff call/issue log, with routing to Sales/Job Order/Software Tasks (raised 2026-09-11, deferred until after Company/Individual)

**Built 2026-09-12 -- see docs/open-business-decisions.md #36** for the
settled rules and `app/models/incidents.py` / `app/routers/incidents.py`
/ `frontend/src/pages/IncidentsPage.tsx` for the implementation. The
Outlook Add-in half is scaffolded but not deployable/testable here --
see `outlook-addin/README.md`. Left below for the original request
wording and design history.

Requested as: Support Staff log incoming calls/issues, which get routed
to Sales (a Quotation), Support (a Job Order), Software Tasks, or
"someone to return call." Explicitly deferred by Dennis until after the
Company/Individual work ("settle company/individual first then new
incident module later") -- recorded here so the design details already
confirmed aren't lost in the meantime.

**Confirmed so far:**

- Converting an Incident **auto-creates** the real target record (a
  Quotation, Job Order, or Software Task pre-filled from the Incident,
  with a back-reference to it) -- not just routing/assigning the
  Incident for someone else to act on manually (confirmed 2026-09-11,
  see docs/open-business-decisions.md #19.7).
- **Outlook integration, confirmed 2026-09-11 as an Outlook Add-in with
  two buttons**, not a fully automatic mailbox-polling approach:
  - **"Convert to Incident"** -- sends the open email's sender,
    subject, and body to the API to create an Incident.
  - **"Convert to Job Order"** -- before allowing this one, the system
    must **check for a valid contract** for that customer first, and
    only allow the conversion if one exists. (Open question: what
    happens when there is no valid contract -- block with an error
    telling the sender to create/find a contract first, or fall back to
    creating an Incident instead and let staff route it manually? Not
    yet decided.)
  - Both buttons are one click each, not automatic -- Support Staff
    still triggers the conversion themselves, reading the email as
    normal first.
  - Needs an Azure AD app registration and Outlook Add-in manifest;
    standard Microsoft Graph/Office Add-in mechanics, nothing exotic.

**Still open** (from the original recording, unchanged): the full
Incident data model (fields, statuses), what "Sales decide Quote or
Directly go to Software Tasks" looks like as a routing UI, and whether
"someone to return Call" creates any record at all or is just an
assignment/reminder.

**Not yet started.** No models, routes, or UI exist for this.

---

## 3. eSignature + eDocument attachments -- all operations and accounting documents (raised 2026-09-12, "put on the waiting list... at the end then we build it in")

Requested as a capability spanning every document in the system (Job
Orders, Service Records, Quotations, Invoices, Receipts, Payment
Vouchers, Purchase Orders, Statements, etc.), explicitly deferred by
Dennis to be built as one pass at the end, not per-document as each is
touched.

**Confirmed so far:**

- **eSignature** on documents -- captured electronically rather than the
  current "Signature & Company Stamp: ___" blank line printed forms
  leave for a physical pen signature. Overlaps with the Support Staff
  mobile app's company-chop-photo + signature workflow (item 1 above),
  which is a specific, more detailed instance of this same need for
  Service Records -- the two should be designed together, not
  separately, when this is picked up.
- **eDocument attachments** -- the ability to attach supporting files
  (photos, PDFs, scanned documents, etc.) to a document record. No
  document type in this system can carry an attachment today; every doc
  is data-only.
- Scope is **every** operations and accounting document, not a specific
  one -- this is a platform capability, not a one-off feature on a
  single form.

**Not yet started -- no models, storage, or UI exist for this.** Real
open questions once this is picked up (not resolved here, just flagged):
what "signing" actually means (drawn signature, typed name + timestamp,
third-party eSign provider like DocuSign, or the mobile app's own
photo-based chop capture), where attachment files are stored (this app
currently only inlines small base64 images for logos -- real file/object
storage is a different scale), size/type/count limits per document, and
whether attachments and signatures follow the same never-delete/
soft-delete posture as every other record here (almost certainly yes,
but not assumed).

---

## 4. eApproval Master -- authority-based, value-gated, multi-staff approvals across documents (raised 2026-09-12)

Requested as a generic approval framework to eventually replace the
one-off approval logic that exists today (Service Record approval,
built specifically and only for Service Records -- see
app/routers/service_records.py / ServiceRecordApprovalPage.tsx) with a
single configurable authority system covering multiple document types.

**Confirmed so far:**

- **Specific authority for specific approvals** -- e.g. Purchase Order
  approval above a certain value requiring an eSignature (this already
  exists in a narrow form as PUR-001's value threshold + owner
  approval, see docs/open-business-decisions.md #4.4 -- eApproval Master
  would generalise that pattern rather than replace its business rule).
- **Payment Voucher preparation approval based on "Bank Authority"** -- a
  new authority concept, distinct from Group Authority (module-level
  CRUD access): who is allowed to prepare/approve a payment against a
  given bank account. Not yet modelled anywhere in this system.
- **Can be more than one staff** -- an authority (e.g. Bank Authority for
  a given account, or PO approval above a threshold) can be assigned to
  multiple people, not just a single approver.
- **Folds in Service Record approval** -- when eApproval Master is
  built, Dennis wants Service Record approval brought into the same
  module rather than staying as its own separate, hard-coded mechanism.
  This is a migration of existing behaviour, not new business rules for
  Service Records themselves (SRV-004 approver-role logic, deduction
  minutes, etc. stay as already confirmed).
- **The approval screen itself, once generic, must:**
  - Show any **attachments** on the document being approved (depends on
    item 3 above existing first).
  - **Never make an approved/rejected item disappear** from the screen
    once acted on -- the approver (and others) must be able to see
    clearly, after the fact, what was **approved**, **rejected**, or is
    still **for review**, with the status visibly distinguishing the
    three states. (Today's Service Record Approval page only lists
    *pending* records -- approved ones drop off the list entirely, since
    that page was built narrowly for the one-time decision. eApproval
    Master's screen is a different, retained-history view.)

**Not yet started -- no models, routes, or UI exist for this.** Depends
on item 3 (attachments) for the "show attachments" requirement to be
meaningful. Real open questions once this is picked up: how an
"authority" is modelled (a new table distinct from Group/GroupModuleAuthority,
or an extension of it), how Bank Authority relates to the existing
BankAccount model (app/models/treasury.py), whether approval is
single-approver-sufficient or requires all assigned approvers, and
exactly which document types move onto this framework first.

---

## 5. Product "Is Stock" flag + Stock Master item selection -- pending Websoft Stock Distribution ERP (raised 2026-09-12)

Requested as: define on the Product Master whether an item is stock-
tracked, ahead of a separate Websoft Stock Distribution ERP project
(a different GitHub repository) that will define the actual stock
inventory flow and documents. Recorded, not built -- the request was
explicitly to "record that" this needs defining, since the logic it
depends on doesn't exist yet.

**Confirmed so far:**

- Product Master needs an **"Is Stock"** flag: ticked means the item's
  quantity needs to be monitored as stock inventory; unticked means it
  doesn't (e.g. a service line item, as most of this catalog is today --
  see app/models/catalog.py `Product`, which has no such flag yet).
- Once Dennis finishes the **Websoft Stock Distribution ERP** (a
  separate project), this system will need to **follow that project's
  Stock Inventory Flow and Documents logic** -- i.e. this app's stock
  handling is meant to mirror/integrate with that other system's design,
  not invent its own.
- **Item selection in documents changes**: once stock exists, choosing a
  line item on a document -- starting with Quotation -- will pick from a
  **Stock Master** instead of today's Product Master, for stock-tracked
  items at least. Whether non-stock (service) items keep using Product
  Master, or everything moves to one merged master, is not stated.

**Not yet started -- no field, model, or UI change made.** Deliberately
so: the Websoft Stock Distribution ERP's own logic doesn't exist yet to
follow, so building against a guessed version of it would very likely
have to be redone. Real open questions once that other project is far
enough along to reference: exact Stock Master field set, how it relates
to (or replaces) today's Product/ProductType model, whether Quotation
Lines/Invoice Lines/PO lines all switch together or one document at a
time, and how stock quantity movements themselves get recorded in this
system (received, issued, adjusted) versus in the Stock Distribution ERP.

---

## 6. Odoo migration program -- Contacts, Subscriptions, Timesheets, Sales Quotations/Invoices/Receipts, Chart of Accounts (raised 2026-09-12)

Requested as: eventually build a migration program to transfer data out
of the existing Odoo system and into this one, mapping Odoo's records
onto this system's equivalent (and differently-named) entities. Recorded
per Dennis's request ("record this that we will eventually also need
a migration program") -- explicitly a future need, not to be built now.

**Confirmed mapping, as given (Odoo source -> Websoft Service ERP target):**

| Odoo | Websoft Service ERP |
|---|---|
| Contacts | Company/Individual (`app/models/company_individuals.py` `CompanyIndividual`) |
| Subscriptions | Contracts (`app/models/contracts.py` `ServiceContract`) |
| Timesheets | Service Records (`app/models/service_records.py`) |
| Sales Quotations | Sales Quote (`app/models/quotations.py` `Quotation`) |
| Sales Invoices | Sales Invoice (`app/models/invoices.py` `Invoice`) |
| (Sales) Receipts | Receipt(s) (`app/models/payments.py` `Payment`, the Receipt Voucher) |
| Chart of Accounts | Chart of Accounts (`app/models/accounting.py` `Account`) |

## 7. WhatsApp OTP as a second login factor (raised 2026-09-12, deferred)

Requested alongside email OTP as: "enhance security with OTP upon
login either email or handphone whatsapp." Email OTP is built (see
docs/open-business-decisions.md #27.3) using the existing SMTP mailer;
WhatsApp OTP is deferred because it needs infrastructure this system
doesn't have yet -- an automated WhatsApp Business API account
(Twilio's WhatsApp API or Meta's Cloud API) that can send a templated
message and have this backend poll/receive the delivery status. Every
other WhatsApp touchpoint in this system today (Print/Email/WhatsApp
icon buttons on documents) is a manual `wa.me` deep link a staff member
opens and sends themselves -- there is no automated send path to build
on. Build once such an account is provisioned: add a `whatsapp_otps`-
style flow mirroring `LoginOtp`, and let the user choose email or
WhatsApp at the OTP step.

This aligns with CLAUDE.md's already-approved Odoo replacement strategy
(phased, module-by-module, with a parallel-run period and no big-bang
migration) and its note that "important historical data will eventually
be migrated" -- this item is the concrete migration-program request for
that strategy, scoped to the record types above.

**Not yet started -- no migration scripts, field-mapping tables, or
import tooling exist.** Real open questions once this is picked up (not
resolved here, just flagged, per CLAUDE.md's "never assume a business
rule when requirements have not been provided"):

1. **Access to Odoo data** -- direct DB access to Odoo's PostgreSQL
   instance, or via Odoo's XML-RPC/JSON-RPC API? Read-only, one-off
   extract, or a repeatable/re-runnable sync during the parallel-run
   period?
2. **Field-level mapping** -- each Odoo model above has many fields;
   which map 1:1 to this system's equivalent model, which need
   transformation (e.g. Odoo's Subscription recurrence/billing fields
   against this system's ServiceContract hours-bucket model, which has
   no direct Odoo equivalent), and which have no target field at all yet.
3. **Identity/reference mapping** -- how an Odoo record's ID is
   correlated with the newly-created Websoft record afterward (for
   re-runs, verification, and so linked records -- e.g. an Invoice's
   Contact -- resolve correctly), and whether that mapping table itself
   needs to be a permanent audit record per this project's "never
   permanently delete" / audit-trail rules.
4. **Historical vs. operational data** -- CLAUDE.md already notes older
   Odoo data "may be archived rather than fully operational"; which of
   the record types above (if any) get imported as read-only/archived
   history versus fully live, editable records.
5. **Numbering/sequence collisions** -- this system generates its own
   document numbers (e.g. `SQ-` quote numbers, `INV-` invoice numbers)
   via `DocumentSequence`; how imported Odoo records get numbered
   (keep Odoo's original reference as a separate field, or renumber into
   this system's sequences) is undecided.
6. **Cut-over sequencing** -- given the phased, parallel-run strategy,
   whether all seven record types migrate together or Company/Individual
   (Contacts) and Chart of Accounts migrate first as foundational/
   reference data, with the transactional documents (Contracts,
   Service Records, Quotes, Invoices, Receipts) following once their
   linked Company/Individual and account records already exist here.
