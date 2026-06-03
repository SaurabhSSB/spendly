# Spec: Login and Logout

## Overview

Implement user authentication: login via email and password, and logout to end the session. Users can authenticate after registration to access protected features. This step establishes Flask session management and password verification, which are foundational for all future authenticated features (profile, expenses, etc.).

## Depends on

- Step 1: Database Setup — requires `users` table and `get_db()` helper
- Step 2: Registration — requires registered users in the database

## Routes

- `POST /login` — process login form submission, authenticate user, create session — public access
- `GET /logout` — clear session and redirect to landing page — logged-in access only

## Database changes

No new tables or columns. Uses existing `users` table created in Step 1.

## Templates

**Modify:**
- `login.html` — add form for email and password input
- `base.html` — add logout button in navigation (visible only when logged in)

## Files to change

- `app.py` — add POST handler for `/login` and implement `/logout`
- `database/db.py` — add helper function to fetch user by email

## Files to create

- None

## New dependencies

No new dependencies. Uses `werkzeug.security.check_password_hash()` (already installed).

## Rules for implementation

- No SQLAlchemy or ORMs — use raw SQLite with parameterized queries only
- Never use string formatting in SQL — always use `?` placeholders
- Passwords must be verified using `werkzeug.security.check_password_hash()`
- Use Flask's `session` object for storing authenticated user ID
- All templates extend `base.html`
- Use `url_for()` for all internal links in templates
- Error handling: use `abort()` for HTTP errors, not bare `return "error string"`
- Validate input:
  - `email`: required, must match a registered user
  - `password`: required, must match the user's hashed password
- Flash or display errors inline in form (via `error` variable in template)
- Redirect to `/profile` on successful login (or appropriate dashboard route)
- Logout must clear the session and redirect to `/` (landing page)
- Enable `PRAGMA foreign_keys = ON` on every database connection via `get_db()`
- Session should be configured with a secret key in `app.py`

## Definition of done

- [ ] `POST /login` route accepts form data from `login.html`
- [ ] Validates email (required, must exist in database)
- [ ] Validates password (required, must match user's hash)
- [ ] Verifies password using `check_password_hash()`
- [ ] Creates session with user ID on successful login
- [ ] Redirects to `/profile` after successful login
- [ ] Displays error messages for invalid email or password
- [ ] `GET /logout` clears session
- [ ] `GET /logout` redirects to `/` (landing page)
- [ ] Logout button visible in navigation only when logged in
- [ ] All database queries use parameterized SQL
- [ ] App runs without errors
- [ ] GET `/login` still renders the login form
- [ ] Users can login with demo credentials (demo@spendly.com / demo123)
