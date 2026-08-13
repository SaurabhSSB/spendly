import pytest

from database import queries
from database.db import get_db


CATEGORIES = ["Food", "Transport", "Bills", "Health", "Entertainment", "Shopping", "Other"]


# ---------------------------------------------------------------- #
# insert_expense (unit tests)                                       #
# ---------------------------------------------------------------- #

def test_insert_expense_valid_row_is_retrievable(app_fixture, seeded_user_no_expenses):
    queries.insert_expense(
        seeded_user_no_expenses["id"], 50.0, "Food", "2026-03-20", "Lunch"
    )

    db = get_db()
    row = db.execute(
        "SELECT user_id, amount, category, date, description FROM expenses WHERE user_id = ?",
        (seeded_user_no_expenses["id"],),
    ).fetchone()
    db.close()

    assert row is not None, "Expected the inserted expense row to be retrievable"
    assert row["user_id"] == seeded_user_no_expenses["id"]
    assert row["amount"] == 50.0
    assert row["category"] == "Food"
    assert row["date"] == "2026-03-20"
    assert row["description"] == "Lunch"


def test_insert_expense_none_description_stored_as_null(app_fixture, seeded_user_no_expenses):
    queries.insert_expense(
        seeded_user_no_expenses["id"], 25.0, "Bills", "2026-04-01", None
    )

    db = get_db()
    row = db.execute(
        "SELECT description FROM expenses WHERE user_id = ?",
        (seeded_user_no_expenses["id"],),
    ).fetchone()
    db.close()

    assert row is not None, "Expected the inserted expense row to be retrievable"
    assert row["description"] is None, "Expected description to be stored as NULL"


# ---------------------------------------------------------------- #
# GET /expenses/add                                                  #
# ---------------------------------------------------------------- #

def test_get_add_expense_unauthenticated_redirects_to_login(client):
    response = client.get("/expenses/add")
    assert response.status_code == 302
    assert "/login" in response.headers["Location"]


def test_get_add_expense_authenticated_returns_200(client, seeded_user):
    with client.session_transaction() as sess:
        sess["user_id"] = seeded_user["id"]
    response = client.get("/expenses/add")
    assert response.status_code == 200


def test_get_add_expense_authenticated_shows_form_and_categories(client, seeded_user):
    with client.session_transaction() as sess:
        sess["user_id"] = seeded_user["id"]
    response = client.get("/expenses/add")
    html = response.data.decode()

    assert "<form" in html, "Expected a form element in the add-expense page"
    assert "POST" in html, "Expected the form method to be POST"
    assert "<select" in html, "Expected a category select element"
    for category in CATEGORIES:
        assert category in html, f"Expected category '{category}' to be present in the form"


# ---------------------------------------------------------------- #
# POST /expenses/add                                                 #
# ---------------------------------------------------------------- #

def test_post_add_expense_unauthenticated_redirects_to_login(client):
    response = client.post(
        "/expenses/add",
        data={
            "amount": "50.0",
            "category": "Food",
            "date": "2026-03-20",
            "description": "Lunch",
        },
    )
    assert response.status_code == 302
    assert "/login" in response.headers["Location"]


def test_post_add_expense_valid_redirects_to_profile(client, seeded_user):
    with client.session_transaction() as sess:
        sess["user_id"] = seeded_user["id"]
    response = client.post(
        "/expenses/add",
        data={
            "amount": "50.0",
            "category": "Food",
            "date": "2026-03-20",
            "description": "Lunch",
        },
    )
    assert response.status_code == 302
    assert "/profile" in response.headers["Location"]


def test_post_add_expense_valid_inserts_row_for_user(client, seeded_user):
    with client.session_transaction() as sess:
        sess["user_id"] = seeded_user["id"]
    client.post(
        "/expenses/add",
        data={
            "amount": "50.0",
            "category": "Food",
            "date": "2026-03-20",
            "description": "Lunch",
        },
    )

    db = get_db()
    row = db.execute(
        "SELECT amount, category, date, description FROM expenses "
        "WHERE user_id = ? AND date = ?",
        (seeded_user["id"], "2026-03-20"),
    ).fetchone()
    db.close()

    assert row is not None, "Expected the new expense to exist in the database"
    assert row["amount"] == 50.0
    assert row["category"] == "Food"
    assert row["description"] == "Lunch"


def test_post_add_expense_missing_amount_rerenders_with_error(client, seeded_user):
    with client.session_transaction() as sess:
        sess["user_id"] = seeded_user["id"]
    response = client.post(
        "/expenses/add",
        data={
            "amount": "",
            "category": "Food",
            "date": "2026-03-20",
            "description": "Lunch",
        },
    )
    html = response.data.decode()

    assert response.status_code == 200
    assert "required" in html.lower() or "error" in html.lower()


def test_post_add_expense_zero_amount_rerenders_with_error(client, seeded_user):
    with client.session_transaction() as sess:
        sess["user_id"] = seeded_user["id"]
    response = client.post(
        "/expenses/add",
        data={
            "amount": "0",
            "category": "Food",
            "date": "2026-03-20",
            "description": "Lunch",
        },
    )
    html = response.data.decode()

    assert response.status_code == 200
    assert "greater than 0" in html or "error" in html.lower()


def test_post_add_expense_non_numeric_amount_rerenders_with_error(client, seeded_user):
    with client.session_transaction() as sess:
        sess["user_id"] = seeded_user["id"]
    response = client.post(
        "/expenses/add",
        data={
            "amount": "not-a-number",
            "category": "Food",
            "date": "2026-03-20",
            "description": "Lunch",
        },
    )
    html = response.data.decode()

    assert response.status_code == 200
    assert "number" in html.lower() or "error" in html.lower()


def test_post_add_expense_invalid_category_rerenders_with_error(client, seeded_user):
    with client.session_transaction() as sess:
        sess["user_id"] = seeded_user["id"]
    response = client.post(
        "/expenses/add",
        data={
            "amount": "50.0",
            "category": "NotACategory",
            "date": "2026-03-20",
            "description": "Lunch",
        },
    )
    html = response.data.decode()

    assert response.status_code == 200
    assert "category" in html.lower()


def test_post_add_expense_invalid_date_rerenders_with_error(client, seeded_user):
    with client.session_transaction() as sess:
        sess["user_id"] = seeded_user["id"]
    response = client.post(
        "/expenses/add",
        data={
            "amount": "50.0",
            "category": "Food",
            "date": "not-a-date",
            "description": "Lunch",
        },
    )
    html = response.data.decode()

    assert response.status_code == 200
    assert "date" in html.lower()


def test_post_add_expense_missing_description_succeeds(client, seeded_user):
    with client.session_transaction() as sess:
        sess["user_id"] = seeded_user["id"]
    response = client.post(
        "/expenses/add",
        data={
            "amount": "15.0",
            "category": "Transport",
            "date": "2026-05-01",
            "description": "",
        },
    )

    assert response.status_code == 302
    assert "/profile" in response.headers["Location"]

    db = get_db()
    row = db.execute(
        "SELECT description FROM expenses WHERE user_id = ? AND date = ?",
        (seeded_user["id"], "2026-05-01"),
    ).fetchone()
    db.close()

    assert row is not None, "Expected the expense with no description to be inserted"
    assert row["description"] is None, "Expected description to be stored as NULL"


def test_post_add_expense_failure_repopulates_sticky_values(client, seeded_user):
    with client.session_transaction() as sess:
        sess["user_id"] = seeded_user["id"]
    response = client.post(
        "/expenses/add",
        data={
            "amount": "not-a-number",
            "category": "Food",
            "date": "2026-07-15",
            "description": "Sticky description",
        },
    )
    html = response.data.decode()

    assert response.status_code == 200
    assert "not-a-number" in html, "Expected previously submitted amount to be echoed back"
    assert "2026-07-15" in html, "Expected previously submitted date to be echoed back"
    assert "Sticky description" in html, "Expected previously submitted description to be echoed back"
