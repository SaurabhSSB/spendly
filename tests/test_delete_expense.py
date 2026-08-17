import pytest
from werkzeug.security import generate_password_hash

from database import queries
from database.db import get_db


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
# delete_expense (unit tests)                                       #
# ---------------------------------------------------------------- #

def test_delete_expense_valid_owner_removes_row(app_fixture, seeded_user):
    expense_id = _get_expense_id(seeded_user["id"], "2026-01-01")
    queries.delete_expense(expense_id, seeded_user["id"])

    db = get_db()
    row = db.execute("SELECT id FROM expenses WHERE id = ?", (expense_id,)).fetchone()
    db.close()

    assert row is None


def test_delete_expense_wrong_owner_leaves_row_unchanged(app_fixture, seeded_user, other_user_with_expense):
    expense_id = _get_expense_id(seeded_user["id"], "2026-01-01")
    queries.delete_expense(expense_id, other_user_with_expense["id"])

    db = get_db()
    row = db.execute("SELECT id FROM expenses WHERE id = ?", (expense_id,)).fetchone()
    db.close()

    assert row is not None


def test_delete_expense_nonexistent_id_no_ops(app_fixture, seeded_user):
    queries.delete_expense(999999, seeded_user["id"])

    db = get_db()
    count = db.execute("SELECT COUNT(*) AS c FROM expenses").fetchone()["c"]
    db.close()

    assert count == 2


# ---------------------------------------------------------------- #
# POST /expenses/<id>/delete                                        #
# ---------------------------------------------------------------- #

def test_post_delete_expense_unauthenticated_redirects_to_login(client, seeded_user):
    expense_id = _get_expense_id(seeded_user["id"], "2026-01-01")
    response = client.post(f"/expenses/{expense_id}/delete")
    assert response.status_code == 302
    assert "/login" in response.headers["Location"]


def test_post_delete_expense_own_expense_redirects_and_removes_row(client, seeded_user):
    expense_id = _get_expense_id(seeded_user["id"], "2026-01-01")
    with client.session_transaction() as sess:
        sess["user_id"] = seeded_user["id"]
    response = client.post(f"/expenses/{expense_id}/delete")

    assert response.status_code == 302
    assert "/profile" in response.headers["Location"]

    db = get_db()
    row = db.execute("SELECT id FROM expenses WHERE id = ?", (expense_id,)).fetchone()
    db.close()

    assert row is None


def test_post_delete_expense_other_users_expense_404s(client, seeded_user, other_user_with_expense):
    with client.session_transaction() as sess:
        sess["user_id"] = seeded_user["id"]
    response = client.post(f"/expenses/{other_user_with_expense['expense_id']}/delete")

    assert response.status_code == 404

    db = get_db()
    row = db.execute(
        "SELECT id FROM expenses WHERE id = ?", (other_user_with_expense["expense_id"],)
    ).fetchone()
    db.close()

    assert row is not None


def test_post_delete_expense_nonexistent_id_404s(client, seeded_user):
    with client.session_transaction() as sess:
        sess["user_id"] = seeded_user["id"]
    response = client.post("/expenses/999999/delete")
    assert response.status_code == 404


def test_get_delete_expense_returns_405(client, seeded_user):
    expense_id = _get_expense_id(seeded_user["id"], "2026-01-01")
    with client.session_transaction() as sess:
        sess["user_id"] = seeded_user["id"]
    response = client.get(f"/expenses/{expense_id}/delete")
    assert response.status_code == 405
