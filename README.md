# find-me backend

A real, tested, multi-tenant API for find-me. This is not a mockup — every
endpoint below was hit with live HTTP requests during development, including
a deliberate attempt by one organization to read, edit, and delete another
organization's data (all three were blocked and verified — see
`test_backend.py`).

## What this proves works right now

- Real signup/login — bcrypt-hashed passwords, JWT bearer tokens
- Real multi-tenant isolation — every write is scoped to the caller's
  organization and enforced server-side, not just hidden in the UI
- Real password reset — a genuine random token with a 30-minute expiry,
  single-use, and the forgot-password endpoint gives an identical response
  whether or not the email exists (so it can't be used to check who has
  an account)
- Real rate limiting — 5 signups/hour and 10 logins/minute per IP,
  actually enforced (see `test_backend.py`, which fires 12 rapid logins
  and confirms a 429 shows up before the 12th)
- Full CRUD for facilities, directory items, staff, and live notices
- Public, unauthenticated reads for the guest-facing side (a QR scan should
  never require a login) alongside authenticated writes for admins
- Structured logging to stdout — every real host, Render included, picks
  this up automatically into a log dashboard with zero extra setup
- Auto-generated, interactive API docs at `/docs`

## What this does NOT do yet

- **Email isn't actually sent yet.** `app/email_utils.py` has the real
  token logic but stubs the send step (logs it instead) — sending a real
  email needs a provider account (SendGrid, SES, Postmark) this
  environment can't create for you. Wiring one in is a small, isolated
  change once you have that account.
- It isn't live on the public internet. It only exists as code + a database
  file until you deploy it somewhere.
- No billing (Stripe isn't wired up).
- No external integrations (PMS, POS, indoor positioning) — see the main
  conversation for what those would be per facility type.
- No email verification on signup — anyone can currently sign up with any
  email address, including one they don't own.
- SQLite, not Postgres. Fine for development and even fine for a first
  handful of real customers; swap before you have serious concurrent write
  load (see below — it's a one-line change).

## Running it locally

```bash
cd backend
pip install -r requirements.txt
uvicorn app.main:app --reload --port 8000
```

Then open `http://localhost:8000/docs` — every endpoint is live and
clickable from there, including a real "Authorize" button that takes a
login and lets you try authenticated requests straight from the browser.

Run the test suite yourself:

```bash
python3 test_backend.py
```

## Deploying it for real

The repo includes `render.yaml` — a Render Blueprint that provisions the web
service and a Postgres database together, wires them to each other, and
generates a secure JWT secret automatically. No manual form-filling.

**1. Push this code to a GitHub repo.**

```bash
cd backend
git init
git add .
git commit -m "find-me backend"
```

Create a new empty repo on GitHub (no README/license — this already has
one), then:

```bash
git remote add origin https://github.com/YOUR-USERNAME/findme-backend.git
git branch -M main
git push -u origin main
```

**2. Sign up at render.com** — no credit card needed for the free tier.

**3. New → Blueprint**, connect the GitHub repo you just pushed. Render
detects `render.yaml` automatically and shows a review page listing exactly
what it's about to create (one web service, one database). Confirm the
database plan shows **Free**, then click **Deploy Blueprint**.

**4. Wait for the build** (a couple of minutes the first time), then open
the URL Render gives you — it'll look like
`https://findme-backend-xxxx.onrender.com`. Check `/health` first, then
`/docs` for the live, clickable API.

**One thing to know about the free tier**: the free Postgres database is
deleted after 30 days. Fine for testing and demoing now — just don't be
surprised if it's gone in a month. When you're ready for this to be
lasting, come back and I'll walk you through upgrading the database plan
(one field change, no code changes).

The free web service also spins down after 15 minutes of no traffic and
takes 30-60 seconds to wake back up on the next request — worth knowing if
you're about to demo this live to someone and don't want an awkward pause.
Hitting `/health` right before a demo wakes it up in advance.

**5. Point the frontend at it.** The existing `find-me.html` frontend reads
everything from an in-memory `BUILDINGS` object. Connecting it for real
means replacing those reads with `fetch()` calls to this API — for example,
`renderHome()` would call `GET /facilities/by-slug/{slug}` instead of
reading `BUILDINGS[state.buildingId]`. This is a genuinely separate piece of
work (rewiring ~30 render functions from sync object reads to async fetch
calls) — happy to start on it now that there's a real URL to actually test
against.

## Before real hotel guests use this

- **Set `CORS_ORIGINS`** to your actual frontend's domain — it defaults to
  allowing everything, which is fine for local dev and logs a warning on
  startup to remind you it's not set.
- **Wire a real email provider** — see the caveat above. Password reset
  and any future "invite a teammate" flow both depend on this.
- **The free database plan** is exactly that — free, and temporary. Upgrade
  it once this is more than a demo.

## Project layout

```
backend/
  app/
    main.py          FastAPI app, rate limiter registration, CORS,
                       router registration, structured logging
    database.py       SQLAlchemy engine/session setup
    models.py         ORM models: Organization, User (now with
                       password-reset token fields), Facility,
                       DirectoryItem, StaffMember, Caution
    schemas.py         Pydantic request/response validation
    auth.py             bcrypt hashing, JWT issue/verify, reset-token
                        generation, the shared rate limiter instance
    email_utils.py       send_email() — real token logic upstream of
                          this, honestly-stubbed send step (see above)
    routers/
      auth.py          signup, login, forgot-password, reset-password —
                        all rate-limited
      facilities.py    Facility CRUD + the get_owned_facility()
                        helper every other router depends on for
                        tenant isolation
      directory.py      Directory item CRUD, nested under a facility
      staff.py            Staff CRUD, nested under a facility
      cautions.py          Live notices, nested under a facility
  test_backend.py         Real test suite — run it against a live server
  requirements.txt
  render.yaml               One-click Blueprint deploy config
```
