# Spec: Backend Route for Profile Page

## Overview
This step adds pytest test coverage for the `GET /profile` backend route and its two supporting database helpers (`get_user_by_id`, `get_expense_summary`). The route and helpers were wired up during Step 04's implementation but have no automated tests. This step creates a `tests/test_profile.py` suite that verifies authentication guards, correct data passing to the template, 404 handling on a missing user record, and accurate expense aggregation — giving the team confidence that the profile backend is correct before expense features build on top of it.

## Depends on
- Step 01 — Database Setup (`users` and `expenses` tables must exist; `get_db()` must work)
- Step 02 — Registration (user records must be insertable)
- Step 03 — Login and Logout (session must store `user_id`)
- Step 04 — Profile Page Design (`profile.html` must exist; route and DB helpers must be implemented)

## Routes
No new routes. The existing `GET /profile` route is what this step tests.

## Database changes
No new tables, columns, or helpers. Uses existing `get_user_by_id(user_id)` and `get_expense_summary(user_id)` from `database/db.py`.

## Templates
No changes.

## Files to change
- None (implementation is complete from Step 04)

## Files to create
- `tests/test_profile.py` — pytest test suite for the profile backend route

## New dependencies
No new dependencies. Uses `pytest` (already in `requirements.txt`).

## Rules for implementation
- No SQLAlchemy or ORMs — use raw SQLite via `get_db()` in test fixtures
- Parameterized queries only — `?` placeholders, never f-strings in SQL
- Tests must use Flask's `app.test_client()` and an in-memory or temporary SQLite database — never touch the production `spendly.db`
- Override `app.config["DATABASE"]` or patch `DB_PATH` in `database/db.py` so tests use a temp file (e.g. `tmp_path / "test.db"`)
- Each test must set up its own isolated DB state via a fixture — no shared mutable state between tests
- All templates extend `base.html` — tests should check `200` status and key content strings, not full HTML equality
- Use `url_for()` awareness: tests should hit `/profile` directly by path, not by constructing URLs manually

## Test cases to cover

### Authentication guard
- `GET /profile` with no session → `302` redirect to `/login`
- `GET /profile` with a valid `user_id` in session → `200`

### Data rendering
- Response body contains the logged-in user's name
- Response body contains the logged-in user's email
- Response body contains a formatted member-since date (year is present at minimum)
- Response body contains the correct expense count for that user
- Response body contains the correct total amount for that user

### Edge cases
- User with zero expenses → count shows `0`, amount shows `0`
- `user_id` in session that does not exist in `users` table → `404`

## Definition of done
- [ ] `pytest tests/test_profile.py` passes with no errors or failures
- [ ] Unauthenticated request to `/profile` returns a 302 redirect to `/login`
- [ ] Authenticated request to `/profile` returns 200
- [ ] Response contains the user's name and email
- [ ] Response contains the correct expense count and total amount
- [ ] A user with no expenses shows count `0` and amount `0`
- [ ] A session referencing a non-existent user ID returns 404
- [ ] Tests use a temporary database — production `spendly.db` is not touched
- [ ] `pytest` (full suite) passes with no regressions
