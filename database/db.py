import os
import sqlite3
from werkzeug.security import generate_password_hash, check_password_hash

DB_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'spendly.db')


def get_db():
    db = sqlite3.connect(DB_PATH)
    db.row_factory = sqlite3.Row
    db.execute('PRAGMA foreign_keys = ON')
    return db


def init_db():
    db = get_db()
    db.executescript('''
        CREATE TABLE IF NOT EXISTS users (
            id            INTEGER PRIMARY KEY AUTOINCREMENT,
            name          TEXT    NOT NULL,
            email         TEXT    UNIQUE NOT NULL,
            password_hash TEXT    NOT NULL,
            created_at    TEXT    DEFAULT (datetime('now'))
        );

        CREATE TABLE IF NOT EXISTS expenses (
            id          INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id     INTEGER NOT NULL REFERENCES users(id),
            amount      REAL    NOT NULL,
            category    TEXT    NOT NULL,
            date        TEXT    NOT NULL,
            description TEXT,
            created_at  TEXT    DEFAULT (datetime('now'))
        );
    ''')
    db.commit()
    db.close()


def seed_db():
    db = get_db()

    row = db.execute('SELECT COUNT(*) FROM users').fetchone()
    if row[0] > 0:
        db.close()
        return

    db.execute(
        'INSERT INTO users (name, email, password_hash) VALUES (?, ?, ?)',
        ('Demo User', 'demo@spendly.com', generate_password_hash('demo123'))
    )
    user_id = db.execute('SELECT last_insert_rowid()').fetchone()[0]

    expenses = [
        (user_id, 12.50,  'Food',          '2026-06-01', 'Morning coffee and croissant'),
        (user_id, 45.00,  'Transport',     '2026-06-03', 'Monthly bus pass top-up'),
        (user_id, 120.00, 'Bills',         '2026-06-05', 'Electricity bill'),
        (user_id, 30.00,  'Health',        '2026-06-08', 'Pharmacy — vitamins'),
        (user_id, 18.99,  'Entertainment', '2026-06-10', 'Streaming subscription'),
        (user_id, 67.40,  'Shopping',      '2026-06-15', 'New running shoes'),
        (user_id, 9.75,   'Other',         '2026-06-18', 'Stationery supplies'),
        (user_id, 34.20,  'Food',          '2026-06-22', 'Grocery run'),
    ]

    db.executemany(
        'INSERT INTO expenses (user_id, amount, category, date, description) VALUES (?, ?, ?, ?, ?)',
        expenses
    )

    db.commit()
    db.close()


def get_user_by_email(email):
    db = get_db()
    user = db.execute(
        'SELECT * FROM users WHERE email = ?',
        (email,)
    ).fetchone()
    db.close()
    return user


def get_user_by_id(user_id):
    db = get_db()
    user = db.execute(
        'SELECT id, name, email, created_at FROM users WHERE id = ?',
        (user_id,)
    ).fetchone()
    db.close()
    return user


def get_expense_summary(user_id):
    db = get_db()
    row = db.execute(
        'SELECT COUNT(*) AS total_count, COALESCE(SUM(amount), 0.0) AS total_amount '
        'FROM expenses WHERE user_id = ?',
        (user_id,)
    ).fetchone()
    db.close()
    return {
        'total_count': row['total_count'],
        'total_amount': row['total_amount'],
    }


def get_expenses(user_id):
    db = get_db()
    rows = db.execute(
        'SELECT id, amount, category, date, description, created_at '
        'FROM expenses WHERE user_id = ? ORDER BY date DESC, id DESC',
        (user_id,)
    ).fetchall()
    db.close()
    return rows


def get_detailed_summary(user_id):
    db = get_db()
    row = db.execute(
        'SELECT COUNT(*) AS total_count, '
        'COALESCE(SUM(amount), 0.0) AS total_amount, '
        'COALESCE(AVG(amount), 0.0) AS avg_amount, '
        'COALESCE(MAX(amount), 0.0) AS max_amount '
        'FROM expenses WHERE user_id = ?',
        (user_id,)
    ).fetchone()
    cat_row = db.execute(
        'SELECT category FROM expenses WHERE user_id = ? '
        'GROUP BY category ORDER BY SUM(amount) DESC LIMIT 1',
        (user_id,)
    ).fetchone()
    db.close()
    return {
        'total_count': row['total_count'],
        'total_amount': row['total_amount'],
        'avg_amount': row['avg_amount'],
        'max_amount': row['max_amount'],
        'top_category': cat_row['category'] if cat_row else 'N/A',
    }


def get_category_breakdown(user_id):
    db = get_db()
    rows = db.execute(
        'SELECT category, COUNT(*) AS count, SUM(amount) AS total '
        'FROM expenses WHERE user_id = ? '
        'GROUP BY category ORDER BY total DESC',
        (user_id,)
    ).fetchall()
    db.close()
    return rows
