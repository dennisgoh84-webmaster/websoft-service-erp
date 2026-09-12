# Websoft Incidents -- Outlook Add-in

A task-pane add-in with two buttons on an open email: **Log as
Incident** and **Convert to Job Order** -- calling this app's own
`/api/incidents/from-email` and `/api/incidents/from-email/convert-to-job-order`
endpoints (see `app/routers/incidents.py`). Confirmed rules for what
these do are in `docs/open-business-decisions.md` #36.

## Status: scaffolded, not deployable or testable as-is

This was built to a real, standard Office Add-in shape (classic XML
manifest, `Office.js`, a task pane), but **cannot be sideloaded or
tested in this environment** -- that needs a real Microsoft 365
tenant/Outlook client and an HTTPS host to serve these files from,
neither of which exist here. Treat this folder as a ready-to-deploy
starting point, not a finished, verified feature.

## A deliberate design choice: no Azure AD / Office SSO

`docs/planned-work.md`'s original note said this "needs an Azure AD
app registration... standard Microsoft Graph/Office Add-in mechanics."
That's true if the add-in should single-sign-on a signed-in Outlook
user straight through to this API. Building and wiring that requires a
real Azure AD tenant and app registration to configure against, which
doesn't exist here -- anything built against a guessed configuration
would very likely need redoing once real credentials exist.

Instead, `taskpane.js` reuses this app's **own existing login**
(`POST /api/auth/login`, the same email/password every staff member
already has) via a plain sign-in form shown once per Outlook session,
token kept in that taskpane's `sessionStorage` only. This is a strictly
smaller, already-working piece of this system -- no Azure AD
registration is needed just to get the two buttons functioning.
Office/Azure AD SSO remains a valid future enhancement (skip the
login form for an already-signed-in Outlook user) but is not required
for this to work, and is not built here.

One consequence: the add-in doesn't yet handle the email-OTP login
step (`docs/open-business-decisions.md` #27.3) -- if OTP is turned on
for an account, that account has to sign into the desktop app once
first (the add-in shows this as an error, it doesn't fail silently).

## Files

- `manifest.xml` -- the classic XML Office Add-in manifest. Every
  `{{HOST}}` placeholder must be replaced with the real hostname this
  is deployed to before sideloading.
- `taskpane.html` / `taskpane.js` -- the panel UI and logic. Loads
  `Office.js` from Microsoft's own CDN (required for any Office
  Add-in; not something this project hosts).
- `assets/icon-{16,32,80}.png` -- placeholder solid-colour icons
  (this app's maroon) so the manifest doesn't reference missing files.
  Replace with real artwork before shipping if wanted -- not required
  for the add-in to function.

## To actually deploy and test this

1. **Host these files over HTTPS.** The simplest option: serve this
   `outlook-addin/` folder from the same nginx container that already
   serves the built React app (see `docker-compose.yml` / `DEPLOY.md`)
   at e.g. `https://your-domain/outlook-addin/`. Outlook refuses to
   load an add-in over plain HTTP.
2. **Replace every `{{HOST}}`** in `manifest.xml` with that real
   hostname.
3. **Sideload the manifest** for testing:
   - Outlook on the web: Settings -> Manage add-ins -> My add-ins ->
     Add a custom add-in -> Add from file, pick `manifest.xml`.
   - Outlook desktop: Get Add-ins -> My add-ins -> Add a custom
     add-in -> Add from file.
   - For a whole organisation instead of just yourself: an admin
     deploys it centrally from the Microsoft 365 admin center
     (Settings -> Integrated apps -> Upload custom app) -- no Azure AD
     app registration needed for this either, since there's no OAuth
     flow to register.
4. **Open any email, click "Log Incident"** in the ribbon to open the
   task pane, sign in once, then use the two buttons.

## Known gaps (flagged, not silently skipped)

- No OTP step in the add-in's own login (see above).
- `API_BASE` in `taskpane.js` is a relative `/api` path, which only
  works if this add-in is hosted on the exact same origin as the
  backend. Hard-code the real API origin there if it's hosted
  elsewhere.
- No automated test coverage -- Outlook Add-ins run inside Outlook's
  own sandboxed webview, which nothing in this repo's toolchain
  (Playwright et al.) can drive.
