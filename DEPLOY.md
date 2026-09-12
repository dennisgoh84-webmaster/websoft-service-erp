# Deploying for Staff Testing

A single-VPS Docker Compose deploy -- frontend (nginx, serving the built
React app) is the only exposed port, and reverse-proxies `/api/*` to the
backend container, so both share one origin (no CORS configuration
needed). Matches CLAUDE.md's approved "Cloud/VPS deployment, portable
to AWS/Azure later" architecture decision.

## 1. Get a VPS

Any small Linux VPS with Docker works -- DigitalOcean, Linode, AWS
Lightsail, a Hetzner box, etc. 1-2 vCPU / 2GB RAM is plenty for a
staff-testing load. Install Docker + the Compose plugin on it (each
provider's "Docker" marketplace image, or the
[official install script](https://docs.docker.com/engine/install/),
already includes both).

## 2. Get the code onto it

```bash
git clone https://github.com/dennisgoh84-webmaster/websoft-service-erp.git
cd websoft-service-erp
git checkout claude/webmaster-erp-setup-qjz74z   # or whichever branch you want to test
```

## 3. Configure secrets

```bash
cp .env.example .env
```

Edit `.env` and fill in:
- `POSTGRES_PASSWORD` -- any strong password, this VPS's own DB only.
- `JWT_SECRET_KEY` -- generate with `openssl rand -hex 32`. Never reuse
  the `dev-only-secret` default in `backend/app/core/config.py`.
- `SMTP_*` -- only if you want the "Email" button (Purchase Order,
  Sales Quotation/Invoice, Receipt/Payment Voucher, Statement of
  Accounts) to actually send. Leave blank to leave Email disabled;
  everything else (Print, Word export, WhatsApp) works regardless.
- `HTTP_PORT` -- leave as `80` unless this box already has something
  else listening there.

## 4. Bring it up

```bash
docker compose up -d --build
```

This builds the backend and frontend images, starts Postgres, runs
`alembic upgrade head` once via the one-shot `migrate` service, then
starts `backend` and `frontend`. Check it's healthy:

```bash
docker compose ps
docker compose logs -f migrate   # confirm migrations applied cleanly
```

Visit `http://<vps-ip>/` (or `http://<vps-ip>:<HTTP_PORT>` if you
changed it). You should see the login page.

## 5. Load data for staff to test against

**Choose one:**

- **Demo data** (fastest way to get staff clicking around): 
  ```bash
  docker compose exec backend uv run python scripts/seed_demo.py
  ```
  ⚠️ **This truncates every table and reseeds from scratch.** Fine for
  a first run on an empty database; **never** run it again once staff
  have entered real test data of their own, or it will wipe it. Gives
  you the demo logins from DEV_SETUP.md (all password `demo1234`):
  `dennis@websoft.local` (owner), `nico@websoft.local` (service_lead),
  `cherish@websoft.local` (sales_manager), `weiling@websoft.local`
  (support_engineer), plus several more seeded users -- see the
  script's own printed summary after it runs.

- **Real staff accounts from day one**: skip seeding, sign in as
  whichever first user you create directly in Postgres (or ask me to
  add a one-off "create first owner" script), then use **Staff Master**
  (Company Setup → Staff Master, once logged in as owner) to add each
  tester with their own login and the right Group Authority.

## 6. Add HTTPS (recommended before sharing the link outside your own network)

The compose file above serves plain HTTP. For a real shared testing
URL, put a TLS-terminating proxy in front of the `frontend` container --
simplest options:
- **Caddy**: a two-line Caddyfile (`your-domain.com { reverse_proxy
  frontend:80 }`) gets you automatic Let's Encrypt HTTPS.
- **nginx + certbot** on the host, proxying to `127.0.0.1:${HTTP_PORT}`.
- A tunnel service (Cloudflare Tunnel, Tailscale Funnel) if you'd
  rather not open inbound ports on the VPS at all.

Ask me to wire up whichever of these you'd prefer, once you have a
domain pointed at the VPS.

## 7. Updating after new pushes

```bash
git pull
docker compose up -d --build
```

`migrate` re-runs on every `up` but Alembic is idempotent (it only
applies migrations not already recorded as run), so this is always
safe -- it will never re-truncate or re-seed data.

## 8. Backups

Postgres data lives in the `db_data` named volume. Back it up
regularly (CLAUDE.md requires backup/recovery):

```bash
docker compose exec db pg_dump -U websoft_app websoft_service_erp | gzip > backup-$(date +%F).sql.gz
```

Restore into a fresh volume with `gunzip -c backup-*.sql.gz | docker
compose exec -T db psql -U websoft_app websoft_service_erp`.
