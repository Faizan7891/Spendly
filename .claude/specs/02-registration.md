# Spec: Registration

## Overview
Implement user registration and login so visitors can create an account and
authenticate into Spendly. This step converts the existing static GET-only
`/register` and `/login` routes into fully working POST handlers backed by
the `users` table, adds Flask session management, and wires up the navbar
to reflect the logged-in state. After this step a user can sign up, sign in,
and land on a placeholder dashboard — the foundation every subsequent feature
builds on.

## Depends on
- Step 01 — Database setup (`users` and `expenses` tables must exist, `get_db()` must be available)

## Routes

| Method | Path | Description | Access |
|--------|------|-------------|--------|
| `GET` | `/register` | Render registration form | Public |
| `POST` | `/register` | Validate form, insert user, redirect to `/login` | Public |
| `GET` | `/login` | Render login form | Public |
| `POST` | `/login` | Validate credentials, create session, redirect to `/dashboard` | Public |
| `GET` | `/dashboard` | Placeholder dashboard for logged-in users | Logged-in |

`/logout` remains a stub (`"coming in Step 3"`) — do not implement it here.

## Database changes
No database changes. The `users` table from Step 01 already has all required
columns (`id`, `name`, `email`, `password_hash`, `created_at`).

## Templates

**Modify:**
- `templates/register.html` — add `value="{{ name }}"` on the name/email inputs
  so the form re-fills after a validation error; ensure `action` is `/register`
- `templates/login.html` — add `value="{{ email }}"` on email input; ensure
  `action` is `/login`
- `templates/base.html` — update `<nav>` to show `Dashboard` + `Log out` links
  when `session.user_id` is set; otherwise keep the current Sign in / Get started links

**Create:**
- `templates/dashboard.html` — minimal logged-in landing page that greets the
  user by name and shows a placeholder message ("Expenses coming in Step 5")

## Files to change
- `app.py` — add `SECRET_KEY`, import session/redirect/request/flash from Flask,
  import `check_password_hash` from werkzeug, implement the five routes above
- `templates/register.html` — sticky inputs + error display (already has `{% if error %}` block)
- `templates/login.html` — sticky email input + error display
- `templates/base.html` — conditional navbar links

## Files to create
- `templates/dashboard.html`

## New dependencies
No new dependencies. `flask` and `werkzeug` are already installed.

## Rules for implementation
- No SQLAlchemy or ORMs — use raw `sqlite3` via `get_db()`
- Parameterised queries only — never use string formatting in SQL
- Passwords hashed and verified with `werkzeug.security`
  (`generate_password_hash` / `check_password_hash`)
- `app.secret_key` must be set before any route uses `session`; use a hard-coded
  dev string for now (e.g. `"spendly-dev-secret"`) — document that it must be
  replaced with an env var before production
- Use CSS variables — never hardcode hex colour values
- All templates extend `base.html`
- Flash messages (`flash()` / `get_flashed_messages()`) are optional; a simple
  `error` template variable passed via `render_template` is acceptable and
  simpler — pick one approach and use it consistently
- Redirect after successful POST (PRG pattern) — never render a template on a
  successful POST

## Definition of done
- [ ] Visiting `/register` shows the registration form
- [ ] Submitting the form with valid data creates a user in `users` and redirects to `/login`
- [ ] Submitting with a duplicate email re-renders the form with an error message and the name/email inputs pre-filled
- [ ] Submitting with a missing field re-renders the form with an error message
- [ ] Visiting `/login` shows the login form
- [ ] Submitting correct credentials creates a session and redirects to `/dashboard`
- [ ] Submitting wrong password or unknown email re-renders the form with a generic error ("Invalid email or password")
- [ ] `/dashboard` is accessible when logged in and shows the user's name
- [ ] Visiting `/dashboard` while logged out redirects to `/login`
- [ ] The navbar shows "Dashboard" and "Log out" links when a session exists
- [ ] The navbar shows "Sign in" and "Get started" when no session exists
- [ ] Passwords are never stored in plain text — only `password_hash` column is written
