import pytest

from database import queries
from database.db import get_db, seed_db


SEED_EXPENSE_TOTAL = 337.84  # actual sum of seed_db()'s 8 seeded expenses
SEED_EXPENSE_COUNT = 8
SEED_TOP_CATEGORY = "Bills"


@pytest.fixture
def demo_user(app_fixture):
    seed_db()
    db = get_db()
    row = db.execute(
        "SELECT id FROM users WHERE email = ?", ("demo@spendly.com",)
    ).fetchone()
    db.close()
    yield {"id": row["id"], "name": "Demo User", "email": "demo@spendly.com"}


# ---------------------------------------------------------------- #
# get_user_by_id                                                    #
# ---------------------------------------------------------------- #

def test_get_user_by_id_valid(app_fixture, seeded_user):
    user = queries.get_user_by_id(seeded_user["id"])
    assert user["name"] == seeded_user["name"]
    assert user["email"] == seeded_user["email"]
    assert user["member_since"]


def test_get_user_by_id_nonexistent(app_fixture):
    assert queries.get_user_by_id(99999) is None


# ---------------------------------------------------------------- #
# get_summary_stats                                                  #
# ---------------------------------------------------------------- #

def test_get_summary_stats_with_expenses(app_fixture, seeded_user):
    stats = queries.get_summary_stats(seeded_user["id"])
    assert stats["total_spent"] == 30.00
    assert stats["transaction_count"] == 2
    assert stats["top_category"] == "Bills"


def test_get_summary_stats_no_expenses(app_fixture, seeded_user_no_expenses):
    stats = queries.get_summary_stats(seeded_user_no_expenses["id"])
    assert stats == {"total_spent": 0, "transaction_count": 0, "top_category": "—"}


# ---------------------------------------------------------------- #
# get_recent_transactions                                            #
# ---------------------------------------------------------------- #

def test_get_recent_transactions_with_expenses(app_fixture, seeded_user):
    transactions = queries.get_recent_transactions(seeded_user["id"])
    assert len(transactions) == 2
    assert transactions[0]["date"] == "2026-01-02"
    assert transactions[1]["date"] == "2026-01-01"
    for txn in transactions:
        assert set(txn.keys()) == {"date", "description", "category", "amount"}


def test_get_recent_transactions_no_expenses(app_fixture, seeded_user_no_expenses):
    assert queries.get_recent_transactions(seeded_user_no_expenses["id"]) == []


# ---------------------------------------------------------------- #
# get_category_breakdown                                            #
# ---------------------------------------------------------------- #

def test_get_category_breakdown_with_expenses(app_fixture, seeded_user):
    breakdown = queries.get_category_breakdown(seeded_user["id"])
    amounts = [cat["amount"] for cat in breakdown]
    assert amounts == sorted(amounts, reverse=True)
    assert all(isinstance(cat["pct"], int) for cat in breakdown)
    assert sum(cat["pct"] for cat in breakdown) == 100


def test_get_category_breakdown_no_expenses(app_fixture, seeded_user_no_expenses):
    assert queries.get_category_breakdown(seeded_user_no_expenses["id"]) == []


# ---------------------------------------------------------------- #
# GET /profile                                                       #
# ---------------------------------------------------------------- #

def test_profile_unauthenticated_redirects(client):
    response = client.get("/profile")
    assert response.status_code == 302
    assert "/login" in response.headers["Location"]


def test_profile_authenticated_seed_user(client, demo_user):
    with client.session_transaction() as sess:
        sess["user_id"] = demo_user["id"]
    response = client.get("/profile")
    html = response.data.decode()

    assert response.status_code == 200
    assert "Demo User" in html
    assert "demo@spendly.com" in html
    assert "₹" in html
    assert f"{SEED_EXPENSE_TOTAL:.2f}" in html
    assert str(SEED_EXPENSE_COUNT) in html
    assert SEED_TOP_CATEGORY in html

    # newest-first ordering: last seeded expense (2026-06-22) appears
    # before the oldest (2026-06-01) in the rendered transaction list.
    assert html.index("2026-06-22") < html.index("2026-06-01")

    breakdown_categories = {"Food", "Transport", "Bills", "Health", "Entertainment", "Shopping", "Other"}
    for category in breakdown_categories:
        assert category in html
