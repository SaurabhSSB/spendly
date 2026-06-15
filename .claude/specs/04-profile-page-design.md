# Spec: Profile Page Design

## Overview
The profile page gives logged-in users a single place to view their account details and a quick summary of their spending activity. It replaces the existing stub at `GET /profile` with a fully rendered, data-driven template that displays the user's name, email, and member-since date alongside two headline stats: total number of expenses recorded and total amount spent. The page is protected — unauthenticated visitors are redirected to login.

## Depends on
- Step 01 — Database Setup (`users` and `expenses` tables must exist)
- Step 02 — Registration (user records must be present)
- Step 03 — Login and Logout (session must store `user_id`)

## Routes
- `GET /profile` — loads and renders the profile page — **logged-in only**

## Database changes
No new tables or columns. Two new helper functions must be added to `database/db.py`:

- `get_user_by_id(user_id)` — returns the user row (id, name, email, created_at) for the given id, or `None` if not found
- `get_expense_summary(user_id)` — returns a dict with `total_count` (int) and `total_amount` (float) for all expenses belonging to the user; returns `{"total_count": 0, "total_amount": 0.0}` when the user has no expenses

Both functions must use parameterized queries (`?` placeholders).

## Templates
- **Create:** `templates/profile.html` — extends `base.html`; displays user name, email, member since date, total expenses count, and total amount spent; includes a logout link using `url_for('logout')`
- **Modify:** none

## Files to change
- `app.py` — replace the stub `profile()` route with an authenticated implementation that calls `get_user_by_id` and `get_expense_summary`, then passes the results to `profile.html`; redirect to `url_for('login')` if `user_id` is not in session
- `database/db.py` — add `get_user_by_id(user_id)` and `get_expense_summary(user_id)` functions

## Files to create
- `templates/profile.html` — full profile template extending `base.html`
- `static/css/profile.css` — page-specific styles using CSS variables only; imported via a `{% block head %}` extra `<link>` tag in `profile.html`

## New dependencies
No new dependencies.

## Rules for implementation
- No SQLAlchemy or ORMs — raw `sqlite3` via `get_db()` only
- Parameterized queries only — `?` placeholders, never f-strings in SQL
- Passwords must not be exposed — do not pass `password_hash` to the template
- Use CSS variables — never hardcode hex color values in `profile.css`
- All templates must extend `base.html`
- DB logic belongs exclusively in `database/db.py` — no inline queries in `app.py`
- Use `abort(404)` if the user record is not found after a valid session lookup
- Use `url_for()` for every internal link in the template — never hardcode paths

## Definition of done
- [ ] Visiting `/profile` without being logged in redirects to `/login`
- [ ] After logging in, visiting `/profile` renders the page without errors
- [ ] The page displays the logged-in user's name and email
- [ ] The page displays the correct "Member since" date (formatted, e.g. "June 2025")
- [ ] The page displays the correct total number of expenses for that user
- [ ] The page displays the correct total amount spent by that user
- [ ] The demo user (`demo@spendly.com`) shows 8 expenses and the correct sum
- [ ] The logout link on the profile page works and clears the session
- [ ] `pytest` passes with no regressions
