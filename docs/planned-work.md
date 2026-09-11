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
