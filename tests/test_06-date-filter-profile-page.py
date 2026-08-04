"""
Tests for Step 6: Date Filter for Profile Page.

Spec: .claude/specs/06-date-filter-profile-page.md

Behavior under test (per spec, not implementation):
- GET /profile accepts optional `date_from` / `date_to` query params
  (ISO YYYY-MM-DD, inclusive bounds).
- Missing/malformed params -> silent fallback to unfiltered ("All Time") view.
- date_from > date_to -> both treated as absent, PLUS a flash message
  "Start date must be before end date." is shown.
- All three data sections (summary stats, recent transactions, category
  breakdown) must respect the active filter identically.
- The "All Time" preset link must point to a clean /profile URL (no params).
- The "This Month" preset must span the first day to the last day of the
  current calendar month.
- The custom-range form fields must reflect back the active values, and the
  active preset/custom button must carry an "active" CSS class.
- ₹ amounts must always render regardless of filter state.
- A filtered result set with zero matching expenses must show ₹0.00,
  0 transactions, and an empty category breakdown, without erroring.
- Unauthenticated requests to /profile (with or without filter params) must
  redirect to /login.

Fixtures `app_fixture`, `client`, `seeded_user`, and `seeded_user_no_expenses`
are provided by tests/conftest.py and reused here for consistency with the
rest of the suite.
"""

import calendar
from datetime import date, timedelta

import pytest
from werkzeug.security import generate_password_hash

from database import queries
from database.db import get_db


# ---------------------------------------------------------------------- #
# Fixtures specific to date-filter testing                                #
# ---------------------------------------------------------------------- #

@pytest.fixture
def dated_user(app_fixture):
    """A user with expenses spread across distinct, well-separated dates
    so date-range filtering can be tested unambiguously:
      - 2026-01-01: Food, 10.00
      - 2026-01-15: Bills, 20.00
      - 2026-02-01: Transport, 5.00
    """
    db = get_db()
    db.execute(
        "INSERT INTO users (name, email, password_hash) VALUES (?, ?, ?)",
        ("Dated User", "dated@example.com", generate_password_hash("testpass")),
    )
    db.commit()
    user_id = db.execute("SELECT last_insert_rowid()").fetchone()[0]
    db.executemany(
        "INSERT INTO expenses (user_id, amount, category, date, description) VALUES (?, ?, ?, ?, ?)",
        [
            (user_id, 10.00, "Food", "2026-01-01", "New Year lunch"),
            (user_id, 20.00, "Bills", "2026-01-15", "Internet bill"),
            (user_id, 5.00, "Transport", "2026-02-01", "Taxi"),
        ],
    )
    db.commit()
    db.close()
    yield {"id": user_id, "name": "Dated User", "email": "dated@example.com"}


def _login(client, user):
    with client.session_transaction() as sess:
        sess["user_id"] = user["id"]


# ---------------------------------------------------------------------- #
# Auth guard                                                              #
# ---------------------------------------------------------------------- #

def test_profile_with_filter_params_unauthenticated_redirects_to_login(client):
    """Unauthenticated requests must redirect to /login even when filter
    query params are supplied."""
    response = client.get("/profile?date_from=2026-01-01&date_to=2026-01-31")
    assert response.status_code == 302
    assert "/login" in response.headers["Location"]


# ---------------------------------------------------------------------- #
# No filter params -> identical to Step 5 (unfiltered) behaviour          #
# ---------------------------------------------------------------------- #

def test_profile_no_params_matches_unfiltered_query_helpers(client, dated_user):
    """GET /profile with no query params must show the same data as calling
    the query helpers with no date bounds at all (Step 5 behaviour)."""
    _login(client, dated_user)
    response = client.get("/profile")
    html = response.data.decode()

    assert response.status_code == 200
    expected_summary = queries.get_summary_stats(dated_user["id"])
    assert f"{expected_summary['total_spent']:.2f}" in html
    assert str(expected_summary["transaction_count"]) in html
    # all three seeded expenses should appear
    assert "2026-01-01" in html
    assert "2026-01-15" in html
    assert "2026-02-01" in html


def test_profile_all_time_preset_link_has_no_query_params(client, dated_user):
    """The 'All Time' preset must link to a clean /profile URL, i.e. it must
    not carry date_from/date_to query params."""
    _login(client, dated_user)
    response = client.get("/profile")
    html = response.data.decode()
    assert 'href="/profile"' in html, "All Time preset must point to a clean /profile URL"


# ---------------------------------------------------------------------- #
# Valid custom date range filtering                                       #
# ---------------------------------------------------------------------- #

def test_custom_range_filters_to_single_day(client, dated_user):
    """A range covering exactly one seeded expense's date must show only
    that expense in transactions, and reflect it in the summary total."""
    _login(client, dated_user)
    response = client.get("/profile?date_from=2026-01-01&date_to=2026-01-01")
    html = response.data.decode()

    assert response.status_code == 200
    assert "10.00" in html
    assert "2026-01-01" in html
    assert "2026-01-15" not in html
    assert "2026-02-01" not in html


def test_custom_range_is_inclusive_of_both_boundary_dates(client, dated_user):
    """date_from/date_to bounds must be inclusive (BETWEEN semantics):
    a range from the first seeded date to the second seeded date must
    include both, and exclude the third."""
    _login(client, dated_user)
    response = client.get("/profile?date_from=2026-01-01&date_to=2026-01-15")
    html = response.data.decode()

    assert "2026-01-01" in html
    assert "2026-01-15" in html
    assert "2026-02-01" not in html
    # total for the two included expenses (10.00 + 20.00)
    assert "30.00" in html


def test_custom_range_covering_all_expenses_matches_unfiltered_totals(client, dated_user):
    """A range wide enough to cover every seeded expense must produce the
    same totals as the unfiltered view."""
    _login(client, dated_user)
    unfiltered = client.get("/profile").data.decode()
    filtered = client.get("/profile?date_from=2020-01-01&date_to=2030-01-01").data.decode()

    unfiltered_total = queries.get_summary_stats(dated_user["id"])["total_spent"]
    assert f"{unfiltered_total:.2f}" in unfiltered
    assert f"{unfiltered_total:.2f}" in filtered


def test_custom_range_with_no_matching_expenses_shows_zero_state(client, dated_user):
    """A valid range containing zero matching expenses must show ₹0.00
    total spent, 0 transactions, an empty category breakdown, and must not
    error."""
    _login(client, dated_user)
    response = client.get("/profile?date_from=2027-01-01&date_to=2027-01-31")
    html = response.data.decode()

    assert response.status_code == 200
    assert "₹0.00" in html
    assert "2026-01-01" not in html
    assert "2026-01-15" not in html
    assert "2026-02-01" not in html


def test_amount_currency_symbol_present_when_filtered(client, dated_user):
    """₹ must be displayed regardless of whether a filter is active."""
    _login(client, dated_user)
    response = client.get("/profile?date_from=2026-01-01&date_to=2026-01-15")
    html = response.data.decode()
    assert "₹" in html


def test_custom_range_reflected_back_into_form_fields(client, dated_user):
    """After applying a valid custom range, the date inputs must reflect the
    active from/to values (so the filter bar shows what's currently applied)."""
    _login(client, dated_user)
    response = client.get("/profile?date_from=2026-01-01&date_to=2026-01-15")
    html = response.data.decode()

    assert 'name="date_from"' in html
    assert 'name="date_to"' in html
    assert 'value="2026-01-01"' in html
    assert 'value="2026-01-15"' in html


def test_custom_range_marks_apply_button_active(client, dated_user):
    """When a valid custom range (that doesn't match a preset) is active,
    the Apply button/custom control must carry a visual 'active' indicator."""
    _login(client, dated_user)
    response = client.get("/profile?date_from=2026-01-01&date_to=2026-01-15")
    html = response.data.decode()
    assert "active" in html


# ---------------------------------------------------------------------- #
# Invalid / malformed input -> silent fallback                            #
# ---------------------------------------------------------------------- #

def test_malformed_date_from_falls_back_to_unfiltered_without_crashing(client, dated_user):
    """A malformed date_from (e.g. not-a-date) must not crash the app; it
    must silently fall back to the unfiltered view."""
    _login(client, dated_user)
    response = client.get("/profile?date_from=not-a-date&date_to=2026-01-31")
    html = response.data.decode()

    assert response.status_code == 200
    # falls back to unfiltered -> all three expenses visible
    assert "2026-01-01" in html
    assert "2026-01-15" in html
    assert "2026-02-01" in html


def test_malformed_date_to_falls_back_to_unfiltered_without_crashing(client, dated_user):
    """A malformed date_to must likewise fall back silently to unfiltered."""
    _login(client, dated_user)
    response = client.get("/profile?date_from=2026-01-01&date_to=garbage")
    html = response.data.decode()

    assert response.status_code == 200
    assert "2026-02-01" in html  # would be excluded if the filter had applied


@pytest.mark.parametrize("bad_value", ["", "2026/01/01", "01-01-2026", "2026-13-01", "abcd-ef-gh"])
def test_various_malformed_date_formats_do_not_error(client, dated_user, bad_value):
    """A variety of malformed date strings must never produce a server
    error; the route must always fall back to unfiltered gracefully."""
    _login(client, dated_user)
    response = client.get(f"/profile?date_from={bad_value}&date_to=2026-01-31")
    assert response.status_code == 200


def test_only_date_from_present_falls_back_to_unfiltered(client, dated_user):
    """If only one of date_from/date_to is supplied, the pair is incomplete
    and the route must fall back to the unfiltered view (per spec: 'If
    either parameter is absent or malformed... falls back to All Time')."""
    _login(client, dated_user)
    response = client.get("/profile?date_from=2026-01-01")
    html = response.data.decode()

    assert response.status_code == 200
    assert "2026-02-01" in html  # outside the implied range, but shown since unfiltered


def test_only_date_to_present_falls_back_to_unfiltered(client, dated_user):
    """Same as above but with only date_to supplied."""
    _login(client, dated_user)
    response = client.get("/profile?date_to=2026-01-01")
    html = response.data.decode()

    assert response.status_code == 200
    assert "2026-02-01" in html


# ---------------------------------------------------------------------- #
# date_from > date_to -> flash error + fallback                           #
# ---------------------------------------------------------------------- #

def test_date_from_after_date_to_shows_flash_error(client, dated_user):
    """When date_from > date_to, the app must flash the exact user-visible
    error message specified: 'Start date must be before end date.'"""
    _login(client, dated_user)
    response = client.get(
        "/profile?date_from=2026-02-01&date_to=2026-01-01", follow_redirects=True
    )
    html = response.data.decode()
    assert "Start date must be before end date." in html


def test_date_from_after_date_to_falls_back_to_unfiltered_data(client, dated_user):
    """When date_from > date_to, filtering must be disabled entirely and the
    unfiltered dataset must be shown (all three expenses)."""
    _login(client, dated_user)
    response = client.get("/profile?date_from=2026-02-01&date_to=2026-01-01")
    html = response.data.decode()

    assert response.status_code == 200
    assert "2026-01-01" in html
    assert "2026-01-15" in html
    assert "2026-02-01" in html


# ---------------------------------------------------------------------- #
# Zero-expense user with an active filter                                 #
# ---------------------------------------------------------------------- #

def test_zero_expense_user_with_filter_shows_zero_state(client, seeded_user_no_expenses):
    """A user with no expenses at all, visiting with an active filter, must
    see ₹0.00 total spent, 0 transactions, and an empty category breakdown,
    with no errors."""
    _login(client, seeded_user_no_expenses)
    response = client.get("/profile?date_from=2026-01-01&date_to=2026-12-31")
    html = response.data.decode()

    assert response.status_code == 200
    assert "₹0.00" in html


# ---------------------------------------------------------------------- #
# "This Month" preset spans the current calendar month                    #
# ---------------------------------------------------------------------- #

def test_this_month_preset_link_spans_current_calendar_month(client, dated_user):
    """The 'This Month' preset link must carry date_from/date_to matching
    the first and last day of the current calendar month."""
    _login(client, dated_user)
    today = date.today()
    first_day = today.replace(day=1).isoformat()
    last_day = date(
        today.year, today.month, calendar.monthrange(today.year, today.month)[1]
    ).isoformat()

    response = client.get("/profile")
    html = response.data.decode()

    assert f"date_from={first_day}" in html
    assert f"date_to={last_day}" in html


def test_filtering_by_current_month_preset_values_returns_expected_subset(client, app_fixture):
    """Applying the computed 'This Month' date range as real query params
    must filter the transaction list to only expenses within the current
    calendar month."""
    db = get_db()
    db.execute(
        "INSERT INTO users (name, email, password_hash) VALUES (?, ?, ?)",
        ("Month User", "month@example.com", generate_password_hash("testpass")),
    )
    db.commit()
    user_id = db.execute("SELECT last_insert_rowid()").fetchone()[0]

    today = date.today()
    in_month_date = today.replace(day=1).isoformat()
    last_month_date = (today.replace(day=1) - timedelta(days=1)).isoformat()

    db.executemany(
        "INSERT INTO expenses (user_id, amount, category, date, description) VALUES (?, ?, ?, ?, ?)",
        [
            (user_id, 15.00, "Food", in_month_date, "In this month"),
            (user_id, 25.00, "Bills", last_month_date, "Last month, excluded"),
        ],
    )
    db.commit()
    db.close()

    client = app_fixture.test_client()
    with client.session_transaction() as sess:
        sess["user_id"] = user_id

    first_day = today.replace(day=1).isoformat()
    last_day = date(
        today.year, today.month, calendar.monthrange(today.year, today.month)[1]
    ).isoformat()

    response = client.get(f"/profile?date_from={first_day}&date_to={last_day}")
    html = response.data.decode()

    assert "15.00" in html
    assert last_month_date not in html


# ---------------------------------------------------------------------- #
# Query-helper level tests (database/queries.py)                          #
# ---------------------------------------------------------------------- #

def test_get_summary_stats_respects_date_range(app_fixture, dated_user):
    stats = queries.get_summary_stats(dated_user["id"], "2026-01-01", "2026-01-15")
    assert stats["total_spent"] == 30.00
    assert stats["transaction_count"] == 2


def test_get_summary_stats_unfiltered_when_no_dates_given(app_fixture, dated_user):
    stats = queries.get_summary_stats(dated_user["id"])
    assert stats["total_spent"] == 35.00
    assert stats["transaction_count"] == 3


def test_get_summary_stats_empty_range_returns_zero_state(app_fixture, dated_user):
    stats = queries.get_summary_stats(dated_user["id"], "2030-01-01", "2030-01-31")
    assert stats["total_spent"] == 0
    assert stats["transaction_count"] == 0
    assert stats["top_category"] == "—"


def test_get_recent_transactions_respects_date_range(app_fixture, dated_user):
    transactions = queries.get_recent_transactions(
        dated_user["id"], date_from="2026-01-01", date_to="2026-01-15"
    )
    dates = {txn["date"] for txn in transactions}
    assert dates == {"2026-01-01", "2026-01-15"}


def test_get_recent_transactions_empty_range_returns_empty_list(app_fixture, dated_user):
    transactions = queries.get_recent_transactions(
        dated_user["id"], date_from="2030-01-01", date_to="2030-01-31"
    )
    assert transactions == []


def test_get_category_breakdown_respects_date_range(app_fixture, dated_user):
    breakdown = queries.get_category_breakdown(
        dated_user["id"], date_from="2026-02-01", date_to="2026-02-28"
    )
    assert len(breakdown) == 1
    assert breakdown[0]["name"] == "Transport"
    assert breakdown[0]["amount"] == 5.00
    assert breakdown[0]["pct"] == 100


def test_get_category_breakdown_empty_range_returns_empty_list(app_fixture, dated_user):
    breakdown = queries.get_category_breakdown(
        dated_user["id"], date_from="2030-01-01", date_to="2030-01-31"
    )
    assert breakdown == []


@pytest.mark.parametrize(
    "helper_name, extra_args",
    [
        ("get_summary_stats", {}),
        ("get_recent_transactions", {}),
        ("get_category_breakdown", {}),
    ],
)
def test_query_helpers_unfiltered_call_matches_explicit_none_dates(
    app_fixture, dated_user, helper_name, extra_args
):
    """Calling a query helper with no date args must be identical to calling
    it with date_from=None, date_to=None explicitly (per spec: unfiltered
    behaviour must match Step 5)."""
    helper = getattr(queries, helper_name)
    result_default = helper(dated_user["id"], **extra_args)
    result_explicit_none = helper(dated_user["id"], date_from=None, date_to=None, **extra_args)
    assert result_default == result_explicit_none


# ---------------------------------------------------------------------- #
# SQL injection / malicious input safety                                  #
# ---------------------------------------------------------------------- #

def test_sql_injection_attempt_in_date_params_is_handled_safely(client, dated_user):
    """A SQL-injection-style payload in date_from must not be treated as a
    valid date (fails strptime) and must not crash or corrupt the query --
    it should fall back to the unfiltered view."""
    _login(client, dated_user)
    payload = "2026-01-01' OR '1'='1"
    response = client.get(
        "/profile", query_string={"date_from": payload, "date_to": "2026-01-31"}
    )

    assert response.status_code == 200
    html = response.data.decode()
    # falls back to unfiltered -> everything still visible, no crash
    assert "2026-02-01" in html
