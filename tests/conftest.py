import pytest
from werkzeug.security import generate_password_hash
import database.db as db_module
from database.db import init_db, get_db
import app as flask_app


@pytest.fixture
def app_fixture(monkeypatch, tmp_path):
    tmp_db = str(tmp_path / "test.db")
    monkeypatch.setattr(db_module, "DB_PATH", tmp_db)
    init_db()
    flask_app.app.config["TESTING"] = True
    flask_app.app.config["SECRET_KEY"] = "test-secret"
    yield flask_app.app


@pytest.fixture
def client(app_fixture):
    yield app_fixture.test_client()


@pytest.fixture
def seeded_user(app_fixture):
    db = get_db()
    db.execute(
        "INSERT INTO users (name, email, password_hash) VALUES (?, ?, ?)",
        ("Test User", "test@example.com", generate_password_hash("testpass")),
    )
    db.commit()
    user_id = db.execute("SELECT last_insert_rowid()").fetchone()[0]
    db.executemany(
        "INSERT INTO expenses (user_id, amount, category, date, description) VALUES (?, ?, ?, ?, ?)",
        [
            (user_id, 10.00, "Food", "2026-01-01", "Lunch"),
            (user_id, 20.00, "Bills", "2026-01-02", "Phone"),
        ],
    )
    db.commit()
    db.close()
    yield {"id": user_id, "name": "Test User", "email": "test@example.com"}


@pytest.fixture
def seeded_user_no_expenses(app_fixture):
    db = get_db()
    db.execute(
        "INSERT INTO users (name, email, password_hash) VALUES (?, ?, ?)",
        ("No Expense User", "noexpense@example.com", generate_password_hash("testpass")),
    )
    db.commit()
    user_id = db.execute("SELECT last_insert_rowid()").fetchone()[0]
    db.close()
    yield {"id": user_id, "name": "No Expense User", "email": "noexpense@example.com"}
