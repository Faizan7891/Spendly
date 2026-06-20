# Spec: Login and Logout

## Overview
Complete the authentication cycle by implementing logout and tightening the
session flow. Login was delivered in Step 02; this step adds the missing half:
`GET /logout` clears the session and returns the user to the landing page.
It also closes two UX gaps left open in Step 02 — logged-in users who visit
`/login` or `/register` should be bounced straight to `/dashboard` rather than
seeing a form they don't need, and when a session guard redirects an anonymous
user to `/login`, the original destination should be preserved via a `next`
parameter so they land back there after signing in.

## Depends on
- Step 01 — Database setup
- Step 02 — Registration (session keys `user_id` / `user_name` must be set on login)

## Routes

| Method | Path | Description | Access |
|--------|------|-------------|--------|
| `GET` | `/logout` | Clear session, redirect to `/` | Logged-in |
| `GET` | `/login?next=<path>` | Existing route — add `next` query-param support | Public |
| `POST` | `/login` | Existing route — redirect to `next` after success if present | Public |

No new routes beyond `/logout`. `/register` and `/login` GET handlers are modified,
not replaced.

## Database changes
No database changes.

## Templates

**Modify:**
- `templates/base.html` — no changes needed; "Log out" link already points to
  `url_for('logout')`

**Create:** None.

## Files to change
- `app.py`
  - `/logout` — replace stub with `session.clear()` then `redirect(url_for('landing'))`
  - `/login` GET — if `session.get("user_id")` already set, redirect to `/dashboard`
  - `/login` POST — after successful auth, redirect to `request.form.get("next") or url_for("dashboard")`
  - `/login` GET — pass `next=request.args.get("next", "")` into the template
  - `/register` GET — if `session.get("user_id")` already set, redirect to `/dashboard`
  - `/dashboard` session guard — pass `next=/dashboard` when redirecting to login:
    `redirect(url_for("login", next="/dashboard"))`

- `templates/login.html`
  - Add a hidden input `<input type="hidden" name="next" value="{{ next or '' }}">` inside the form
    so the `next` value survives the POST

## Files to create
None.

## New dependencies
No new dependencies.

## Rules for implementation
- No SQLAlchemy or ORMs — use raw `sqlite3` via `get_db()`
- Parameterised queries only — never use string formatting in SQL
- Passwords hashed with `werkzeug.security`
- Use CSS variables — never hardcode hex values
- All templates extend `base.html`
- Redirect after every successful POST (PRG pattern)
- `next` redirect safety — only redirect to relative paths. Check that the
  `next` value starts with `/` before using it; if not, fall back to
  `url_for("dashboard")`. This prevents open-redirect attacks.
- `session.clear()` not `session.pop()` — clears all keys at once

## Definition of done
- [ ] Clicking "Log out" in the navbar clears the session and lands on the landing page (`/`)
- [ ] After logout, visiting `/dashboard` redirects to `/login`
- [ ] After logout, the navbar shows "Sign in" and "Get started" (not Dashboard/Log out)
- [ ] A logged-in user visiting `/login` is redirected to `/dashboard` automatically
- [ ] A logged-in user visiting `/register` is redirected to `/dashboard` automatically
- [ ] Visiting `/dashboard` while logged out redirects to `/login?next=/dashboard`
- [ ] After signing in from that redirect, the user lands on `/dashboard` (not a generic redirect)
- [ ] A `next` value that does not start with `/` is ignored (open-redirect protection)
