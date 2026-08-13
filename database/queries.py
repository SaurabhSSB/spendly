from database.db import get_db

MONTH_NAMES = [
    "January", "February", "March", "April", "May", "June",
    "July", "August", "September", "October", "November", "December",
]


def _format_member_since(created_at):
    year, month = created_at[:7].split("-")
    return f"{MONTH_NAMES[int(month) - 1]} {year}"


def get_user_by_id(user_id):
    db = get_db()
    row = db.execute(
        "SELECT name, email, created_at FROM users WHERE id = ?",
        (user_id,)
    ).fetchone()
    db.close()
    if row is None:
        return None
    return {
        "name": row["name"],
        "email": row["email"],
        "member_since": _format_member_since(row["created_at"]),
    }


def _date_range_clause(date_from, date_to, params):
    if date_from and date_to:
        params.append(date_from)
        params.append(date_to)
        return " AND date BETWEEN ? AND ?"
    return ""


def get_summary_stats(user_id, date_from=None, date_to=None):
    db = get_db()
    params = [user_id]
    clause = _date_range_clause(date_from, date_to, params)
    totals = db.execute(
        "SELECT COUNT(*) AS transaction_count, COALESCE(SUM(amount), 0) AS total_spent "
        "FROM expenses WHERE user_id = ?" + clause,
        tuple(params)
    ).fetchone()
    top = db.execute(
        "SELECT category FROM expenses WHERE user_id = ?" + clause +
        " GROUP BY category ORDER BY SUM(amount) DESC LIMIT 1",
        tuple(params)
    ).fetchone()
    db.close()
    return {
        "total_spent": totals["total_spent"],
        "transaction_count": totals["transaction_count"],
        "top_category": top["category"] if top else "—",
    }


def get_recent_transactions(user_id, limit=10, date_from=None, date_to=None):
    db = get_db()
    params = [user_id]
    clause = _date_range_clause(date_from, date_to, params)
    params.append(limit)
    rows = db.execute(
        "SELECT date, description, category, amount FROM expenses "
        "WHERE user_id = ?" + clause + " ORDER BY date DESC, id DESC LIMIT ?",
        tuple(params)
    ).fetchall()
    db.close()
    return [
        {
            "date": row["date"],
            "description": row["description"],
            "category": row["category"],
            "amount": row["amount"],
        }
        for row in rows
    ]


def get_category_breakdown(user_id, date_from=None, date_to=None):
    db = get_db()
    params = [user_id]
    clause = _date_range_clause(date_from, date_to, params)
    rows = db.execute(
        "SELECT category, SUM(amount) AS total FROM expenses "
        "WHERE user_id = ?" + clause + " GROUP BY category ORDER BY total DESC",
        tuple(params)
    ).fetchall()
    db.close()

    if not rows:
        return []

    total_all = sum(row["total"] for row in rows)
    pcts = [int((row["total"] / total_all) * 100) for row in rows]
    pcts[0] += 100 - sum(pcts)

    return [
        {"name": row["category"], "amount": row["total"], "pct": pct}
        for row, pct in zip(rows, pcts)
    ]


def insert_expense(user_id, amount, category, expense_date, description):
    db = get_db()
    db.execute(
        "INSERT INTO expenses (user_id, amount, category, date, description) "
        "VALUES (?, ?, ?, ?, ?)",
        (user_id, amount, category, expense_date, description)
    )
    db.commit()
    db.close()
