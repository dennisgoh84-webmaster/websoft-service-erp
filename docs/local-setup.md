# Local Setup Guide

Run the full Websoft Service ERP stack on your own PC — nothing is
exposed to the internet, everything stays on `localhost`.

---

## Prerequisites

You only need two things installed on your PC:

### 1. Docker Desktop

Download from: **https://www.docker.com/products/docker-desktop/**

- Pick "Docker Desktop for Windows" or "Docker Desktop for Mac"
- Run the installer, accept defaults
- Open Docker Desktop after install — it needs to be running before you
  can use `docker compose`
- On Windows it may ask you to enable WSL 2 — follow the prompts, it
  walks you through it

### 2. Git

- **Windows:** Download from **https://git-scm.com/download/win** — run
  the installer with defaults. This gives you "Git Bash" (a terminal)
  which you can use for all the commands below.
- **macOS:** Open Terminal and type `git --version` — if it's not
  installed, macOS will prompt you to install the Xcode Command Line
  Tools (say yes). Or install via **https://git-scm.com/download/mac**.

That's it — no Python, Node, or Postgres install needed. Docker handles
all of that inside the containers.

---

## 1. Clone the repo

```bash
git clone https://github.com/dennisgoh84-webmaster/websoft-service-erp.git
cd websoft-service-erp
```

## 2. Create your `.env` file

```bash
cp .env.example .env
```

Open `.env` in any text editor (Notepad, VS Code, whatever you have)
and fill in these two required values:

```dotenv
# Pick any strong password — this is only used inside Docker between
# containers, never exposed to the internet. Example:
POSTGRES_PASSWORD=MyL0calTestPw!2026

# A random secret for login tokens. Generate it by running one of these
# in your terminal and pasting the output:
#
#   On Git Bash / macOS Terminal:
#     openssl rand -hex 32
#
#   On PowerShell (if you don't have openssl):
#     -join ((1..32) | ForEach-Object { '{0:x2}' -f (Get-Random -Max 256) })
#
# Either command prints a 64-character hex string. Paste that here:
JWT_SECRET_KEY=paste-the-64-char-hex-string-here
```

### Optional settings

| Variable | Default | Notes |
|---|---|---|
| `HTTP_PORT` | `80` | Change to e.g. `8080` if port 80 is already in use |
| `SMTP_HOST` | _(blank)_ | Leave blank to skip email — Print, WhatsApp, and Word export still work |
| `SMTP_PORT` | `587` | |
| `SMTP_USERNAME` | _(blank)_ | |
| `SMTP_PASSWORD` | _(blank)_ | |
| `SMTP_FROM_EMAIL` | _(blank)_ | |
| `SMTP_FROM_NAME` | `Web Master Consultancy` | |

## 3. Build and start

```bash
docker compose up --build -d
```

This does four things automatically, in order:

1. **Postgres** starts and waits until healthy.
2. **Migrate** runs all Alembic migrations against the empty database,
   then exits.
3. **Backend** (FastAPI) starts on an internal port.
4. **Frontend** (nginx + React) starts and reverse-proxies `/api/*` to
   the backend — this is the only container with a host port mapping.

First build takes a few minutes (downloading base images, installing
dependencies). Subsequent starts are fast.

### Check it's running

```bash
docker compose ps
```

You should see `db`, `backend`, and `frontend` all showing `running`
(and `migrate` showing `exited (0)` — that's expected, it runs once and
stops).

## 4. Seed demo data

The database starts empty. To get demo companies, users, contracts, job
orders, invoices, and everything else needed to click around immediately:

```bash
docker compose exec backend uv run python scripts/seed_demo.py
```

### Demo logins

| User | Email | Password | Role |
|---|---|---|---|
| Dennis Goh | dennis@websoft.local | demo1234 | Owner |
| Nico | nico@websoft.local | demo1234 | Service Lead |
| Cherish | cherish@websoft.local | demo1234 | Sales Manager |
| Wei Ling | weiling@websoft.local | demo1234 | Support Engineer |

> **Note:** First login with a seeded account will prompt a forced
> password change (security policy). Pick any new password that's at
> least 8 characters with letters and numbers.

## 5. Open in browser

```
http://localhost
```

(or `http://localhost:8080` if you changed `HTTP_PORT`)

---

## Day-to-day commands

| Task | Command |
|---|---|
| Start the stack | `docker compose up -d` |
| Stop the stack | `docker compose down` |
| Stop and **delete all data** | `docker compose down -v` |
| View backend logs | `docker compose logs -f backend` |
| View all logs | `docker compose logs -f` |
| Re-run migrations (after a pull) | `docker compose up migrate` |
| Re-seed from scratch | `docker compose down -v && docker compose up --build -d && docker compose exec backend uv run python scripts/seed_demo.py` |
| Rebuild after code changes | `docker compose up --build -d` |

---

## Pulling updates

When new code is pushed to the repo:

```bash
git pull origin main
docker compose up --build -d
docker compose up migrate        # runs any new migrations
```

If the schema changed in a way that's incompatible with existing data
(rare — migrations handle most changes), reset from scratch:

```bash
docker compose down -v
docker compose up --build -d
docker compose exec backend uv run python scripts/seed_demo.py
```

---

## Troubleshooting

**Port 80 already in use**
Set `HTTP_PORT=8080` (or any free port) in `.env`, then
`docker compose up -d`.

**"Cannot connect to the Docker daemon"**
Docker Desktop isn't running — open it first.

**Backend keeps restarting**
Check logs: `docker compose logs backend`. Most common cause is a
missing or invalid `JWT_SECRET_KEY` in `.env`.

**Database connection refused**
The `db` container might still be starting. Wait a few seconds and
retry — the backend will reconnect automatically once Postgres is
healthy.

**Want a completely fresh start**
`docker compose down -v` deletes the database volume. Then rebuild and
re-seed.
