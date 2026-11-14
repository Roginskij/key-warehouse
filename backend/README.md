# KeyVerhaus — backend

Python 3.12, FastAPI, PostgreSQL, SQLAlchemy 2 (async), Alembic, uv.

## Run locally (Postgres.app)

1. Start Postgres.app, then create databases once:
   ```bash
   createdb key_warehouse
   createdb key_warehouse_test
   ```
2. Settings: `cp .env.example .env` and set `JWT_SECRET`.
3. Install and migrate:
   ```bash
   uv sync
   uv run alembic upgrade head
   ```
4. Create your superadmin account (asks for the password):
   ```bash
   uv run python -m app.cli create-superadmin --email you@example.com --name "Your Name"
   ```
5. Optional — a demo workshop owner (not an admin) with sample stock:
   ```bash
   uv run python -m app.seed_demo
   ```
   E-mail and password are written to `dev-accounts.local.md` (git-ignored).
6. Start the API:
   ```bash
   uv run uvicorn app.main:app --reload
   ```
   API docs: http://localhost:8000/docs

E-mails (confirmation, password reset, invitations): locally they go to **Mailpit**
(started by `docker compose up -d mailpit`), open http://localhost:8025 to read them and
click the links. `.env`: `EMAIL_BACKEND=smtp`, `SMTP_HOST=localhost`, `SMTP_PORT=1025`,
`SMTP_STARTTLS=false`. Without Mailpit use `EMAIL_BACKEND=console` (mails are printed
to the server log). Production: Brevo SMTP credentials in `.env`.

## Run with Docker (alternative)

```bash
docker compose up --build
```
Starts Postgres, the API on :8000 and Mailpit (catches e-mails, UI on http://localhost:8025).

## Tests

```bash
uv run pytest
```
Tests rebuild the `key_warehouse_test` database from migrations on every run.

## Structure

```
app/
  core/          config, DB, security, errors, e-mail, i18n
  modules/
    auth/        register, verify e-mail, login, refresh, logout, password reset/change
    users/       profile (/users/me), account deletion (GDPR)
    workshops/   workshops, members, roles, invitations
    admin/       admin panel: users, permissions
    catalog/     global key catalog: items, codes, merge/split, proposals queue, import
    inventory/   workshop stock: items, locations, movements, rates, Excel import/export
    reference/   countries, currencies, trade zones, languages
alembic/         DB migrations
tests/
```

New DB change: edit models → `uv run alembic revision --autogenerate -m "..."` →
review the file → `uv run alembic upgrade head`.
