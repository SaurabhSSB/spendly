import pytest
from werkzeug.security import generate_password_hash

from database import queries
from database.db import get_db


CATEGORIES = ["Food", "Transport", "Bills", "Health", "Entertainment", "Shopping", "Other"]


@pytest.fixture
def other_user_with_expense(app_fixture):
    db = get_db()
    db.execute(
        "INSERT INTO users (name, email, password_hash) VALUES (?, ?, ?)",
        ("Other User", "other@example.com", generate_password_hash("testpass")),
    )
    db.commit()
    user_id = db.execute("SELECT last_insert_rowid()").fetchone()[0]
    db.execute(
        "INSERT INTO expenses (user_id, amount, category, date, description) VALUES (?, ?, ?, ?, ?)",
        (user_id, 99.00, "Shopping", "2026-02-01", "Not yours"),
    )
    db.commit()
    expense_id = db.execute("SELECT last_insert_rowid()").fetchone()[0]
    db.close()
    yield {"id": user_id, "expense_id": expense_id}


def _get_expense_id(user_id, date_str):
    db = get_db()
    row = db.execute(
        "SELECT id FROM expenses WHERE user_id = ? AND date = ?", (user_id, date_str)
    ).fetchone()
    db.close()
    return row["id"]


# ---------------------------------------------------------------- #
# get_expense_by_id (unit tests)                                    #
# ---------------------------------------------------------------- #

def test_get_expense_by_id_valid_owner(app_fixture, seeded_user):
    expense_id = _get_expense_id(seeded_user["id"], "2026-01-01")
    expense = queries.get_expense_by_id(expense_id, seeded_user["id"])

    assert expense is not None
    assert expense["amount"] == 10.00
    assert expense["category"] == "Food"
    assert expense["date"] == "2026-01-01"
    assert expense["description"] == "Lunch"


def test_get_expense_by_id_wrong_owner(app_fixture, seeded_user, other_user_with_expense):
    expense_id = _get_expense_id(seeded_user["id"], "2026-01-01")
    assert queries.get_expense_by_id(expense_id, other_user_with_expense["id"]) is None


def test_get_expense_by_id_nonexistent(app_fixture, seeded_user):
    assert queries.get_expense_by_id(999999, seeded_user["id"]) is None


# ---------------------------------------------------------------- #
# update_expense (unit tests)                                       #
# ---------------------------------------------------------------- #

def test_update_expense_valid_owner_updates_row(app_fixture, seeded_user):
    expense_id = _get_expense_id(seeded_user["id"], "2026-01-01")
    queries.update_expense(expense_id, seeded_user["id"], 99.0, "Bills", "2026-01-05", "Updated")

    db = get_db()
    row = db.execute("SELECT amount, category, date, description FROM expenses WHERE id = ?", (expense_id,)).fetchone()
    db.close()

    assert row["amount"] == 99.0
    assert row["category"] == "Bills"
    assert row["date"] == "2026-01-05"
    assert row["description"] == "Updated"


def test_update_expense_wrong_owner_leaves_row_unchanged(app_fixture, seeded_user, other_user_with_expense):
    expense_id = _get_expense_id(seeded_user["id"], "2026-01-01")
    queries.update_expense(expense_id, other_user_with_expense["id"], 99.0, "Bills", "2026-01-05", "Updated")

    db = get_db()
    row = db.execute("SELECT amount, category, date, description FROM expenses WHERE id = ?", (expense_id,)).fetchone()
    db.close()

    assert row["amount"] == 10.00
    assert row["category"] == "Food"
    assert row["date"] == "2026-01-01"
    assert row["description"] == "Lunch"


# ---------------------------------------------------------------- #
# GET /expenses/<id>/edit                                            #
# ---------------------------------------------------------------- #

def test_get_edit_expense_unauthenticated_redirects_to_login(client, seeded_user):
    expense_id = _get_expense_id(seeded_user["id"], "2026-01-01")
    response = client.get(f"/expenses/{expense_id}/edit")
    assert response.status_code == 302
    assert "/login" in response.headers["Location"]


def test_get_edit_expense_authenticated_own_expense(client, seeded_user):
    expense_id = _get_expense_id(seeded_user["id"], "2026-01-01")
    with client.session_transaction() as sess:
        sess["user_id"] = seeded_user["id"]
    response = client.get(f"/expenses/{expense_id}/edit")
    html = response.data.decode()

    assert response.status_code == 200
    assert "<form" in html
    assert "10.0" in html or "10" in html
    assert "2026-01-01" in html
    assert "Lunch" in html
    assert f'value="Food" selected' in html


def test_get_edit_expense_other_users_expense_404s(client, seeded_user, other_user_with_expense):
    with client.session_transaction() as sess:
        sess["user_id"] = seeded_user["id"]
    response = client.get(f"/expenses/{other_user_with_expense['expense_id']}/edit")
    assert response.status_code == 404


def test_get_edit_expense_nonexistent_id_404s(client, seeded_user):
    with client.session_transaction() as sess:
        sess["user_id"] = seeded_user["id"]
    response = client.get("/expenses/999999/edit")
    assert response.status_code == 404


# ---------------------------------------------------------------- #
# POST /expenses/<id>/edit                                           #
# ---------------------------------------------------------------- #

def test_post_edit_expense_unauthenticated_redirects_to_login(client, seeded_user):
    expense_id = _get_expense_id(seeded_user["id"], "2026-01-01")
    response = client.post(
        f"/expenses/{expense_id}/edit",
        data={"amount": "50.0", "category": "Food", "date": "2026-03-20", "description": "Lunch"},
    )
    assert response.status_code == 302
    assert "/login" in response.headers["Location"]


def test_post_edit_expense_valid_redirects_and_updates_db(client, seeded_user):
    expense_id = _get_expense_id(seeded_user["id"], "2026-01-01")
    with client.session_transaction() as sess:
        sess["user_id"] = seeded_user["id"]
    response = client.post(
        f"/expenses/{expense_id}/edit",
        data={"amount": "75.5", "category": "Health", "date": "2026-03-20", "description": "Checkup"},
    )
    assert response.status_code == 302
    assert "/profile" in response.headers["Location"]

    db = get_db()
    row = db.execute("SELECT amount, category, date, description FROM expenses WHERE id = ?", (expense_id,)).fetchone()
    db.close()

    assert row["amount"] == 75.5
    assert row["category"] == "Health"
    assert row["date"] == "2026-03-20"
    assert row["description"] == "Checkup"


def test_post_edit_expense_other_users_expense_404s(client, seeded_user, other_user_with_expense):
    with client.session_transaction() as sess:
        sess["user_id"] = seeded_user["id"]
    response = client.post(
        f"/expenses/{other_user_with_expense['expense_id']}/edit",
        data={"amount": "50.0", "category": "Food", "date": "2026-03-20", "description": "Lunch"},
    )
    assert response.status_code == 404


def test_post_edit_expense_missing_amount_rerenders_with_error(client, seeded_user):
    expense_id = _get_expense_id(seeded_user["id"], "2026-01-01")
    with client.session_transaction() as sess:
        sess["user_id"] = seeded_user["id"]
    response = client.post(
        f"/expenses/{expense_id}/edit",
        data={"amount": "", "category": "Food", "date": "2026-03-20", "description": "Lunch"},
    )
    html = response.data.decode()

    assert response.status_code == 200
    assert "required" in html.lower() or "error" in html.lower()


def test_post_edit_expense_zero_amount_rerenders_with_error(client, seeded_user):
    expense_id = _get_expense_id(seeded_user["id"], "2026-01-01")
    with client.session_transaction() as sess:
        sess["user_id"] = seeded_user["id"]
    response = client.post(
        f"/expenses/{expense_id}/edit",
        data={"amount": "0", "category": "Food", "date": "2026-03-20", "description": "Lunch"},
    )
    html = response.data.decode()

    assert response.status_code == 200
    assert "greater than 0" in html or "error" in html.lower()


def test_post_edit_expense_non_numeric_amount_rerenders_with_error(client, seeded_user):
    expense_id = _get_expense_id(seeded_user["id"], "2026-01-01")
    with client.session_transaction() as sess:
        sess["user_id"] = seeded_user["id"]
    response = client.post(
        f"/expenses/{expense_id}/edit",
        data={"amount": "not-a-number", "category": "Food", "date": "2026-03-20", "description": "Lunch"},
    )
    html = response.data.decode()

    assert response.status_code == 200
    assert "number" in html.lower() or "error" in html.lower()


def test_post_edit_expense_invalid_category_rerenders_with_error(client, seeded_user):
    expense_id = _get_expense_id(seeded_user["id"], "2026-01-01")
    with client.session_transaction() as sess:
        sess["user_id"] = seeded_user["id"]
    response = client.post(
        f"/expenses/{expense_id}/edit",
        data={"amount": "50.0", "category": "NotACategory", "date": "2026-03-20", "description": "Lunch"},
    )
    html = response.data.decode()

    assert response.status_code == 200
    assert "category" in html.lower()


def test_post_edit_expense_invalid_date_rerenders_with_error(client, seeded_user):
    expense_id = _get_expense_id(seeded_user["id"], "2026-01-01")
    with client.session_transaction() as sess:
        sess["user_id"] = seeded_user["id"]
    response = client.post(
        f"/expenses/{expense_id}/edit",
        data={"amount": "50.0", "category": "Food", "date": "not-a-date", "description": "Lunch"},
    )
    html = response.data.decode()

    assert response.status_code == 200
    assert "date" in html.lower()


def test_post_edit_expense_missing_description_succeeds(client, seeded_user):
    expense_id = _get_expense_id(seeded_user["id"], "2026-01-01")
    with client.session_transaction() as sess:
        sess["user_id"] = seeded_user["id"]
    response = client.post(
        f"/expenses/{expense_id}/edit",
        data={"amount": "15.0", "category": "Transport", "date": "2026-05-01", "description": ""},
    )
    assert response.status_code == 302
    assert "/profile" in response.headers["Location"]

    db = get_db()
    row = db.execute("SELECT description FROM expenses WHERE id = ?", (expense_id,)).fetchone()
    db.close()

    assert row["description"] is None


def test_post_edit_expense_failure_repopulates_sticky_values(client, seeded_user):
    expense_id = _get_expense_id(seeded_user["id"], "2026-01-01")
    with client.session_transaction() as sess:
        sess["user_id"] = seeded_user["id"]
    response = client.post(
        f"/expenses/{expense_id}/edit",
        data={
            "amount": "not-a-number",
            "category": "Food",
            "date": "2026-07-15",
            "description": "Sticky description",
        },
    )
    html = response.data.decode()

    assert response.status_code == 200
    assert "not-a-number" in html
    assert "2026-07-15" in html
    assert "Sticky description" in html
