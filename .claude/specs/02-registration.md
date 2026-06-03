# Spec: Registration

## Overview

Implement user registration functionality. Users can sign up with a name, email, and password. The system validates input, checks for duplicate emails, hashes passwords, and stores new users in the database. Registration is the second foundational step that enables all future authenticated features.

## Depends on

- Step 1: Database Setup — requires working `users` table and `get_db()` helper

## Routes

- `POST /register` — process registration form submission, validate, insert user — public access

## Database changes

No new tables or columns. Uses existing `users` table created in Step 1.

## Templates

**Modify:**
- `register.html` — already structured, no layout changes needed

## Files to change

- `app.py` — add POST route handler for `/register`

## Files to create

- None

## New dependencies

No new dependencies.

## Rules for implementation

- No SQLAlchemy or ORMs — use raw SQLite with parameterized queries only
- Never use string formatting in SQL — always use `?` placeholders
- Passwords must be hashed using `werkzeug.security.generate_password_hash()`
- All templates extend `base.html`
- Use `url_for()` for all internal links in templates
- Error handling: use `abort()` for HTTP errors, not bare `return "error string"`
- Validate input:
  - `name`: required, non-empty, max 255 characters
  - `email`: required, valid email format, must be unique
  - `password`: required, minimum 8 characters
- Handle constraint violations gracefully (duplicate email)
- Redirect to `/login` on successful registration
- Flash or display errors inline in form (via `error` variable in template)
- Enable `PRAGMA foreign_keys = ON` on every database connection via `get_db()`

## Definition of done

- [ ] `POST /register` route accepts form data from `register.html`
- [ ] Validates name (non-empty, ≤255 chars)
- [ ] Validates email (non-empty, valid format, unique in database)
- [ ] Validates password (non-empty, ≥8 characters)
- [ ] Hashes password before storing
- [ ] Inserts user into `users` table on valid input
- [ ] Handles duplicate email gracefully with error message
- [ ] Handles other validation errors with clear messages
- [ ] Redirects to `/login` after successful registration
- [ ] Form displays error messages in the error section
- [ ] All database queries use parameterized SQL
- [ ] App runs without errors
- [ ] GET `/register` still renders the registration form
