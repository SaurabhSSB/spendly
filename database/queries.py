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


def get_summary_stats(user_id):
    db = get_db()
    totals = db.execute(
        "SELECT COUNT(*) AS transaction_count, COALESCE(SUM(amount), 0) AS total_spent "
        "FROM expenses WHERE user_id = ?",
        (user_id,)
    ).fetchone()
    top = db.execute(
        "SELECT category FROM expenses WHERE user_id = ? "
        "GROUP BY category ORDER BY SUM(amount) DESC LIMIT 1",
        (user_id,)
    ).fetchone()
    db.close()
    return {
        "total_spent": totals["total_spent"],
        "transaction_count": totals["transaction_count"],
        "top_category": top["category"] if top else "—",
    }


def get_recent_transactions(user_id, limit=10):
    db = get_db()
    rows = db.execute(
        "SELECT date, description, category, amount FROM expenses "
        "WHERE user_id = ? ORDER BY date DESC, id DESC LIMIT ?",
        (user_id, limit)
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


def get_category_breakdown(user_id):
    db = get_db()
    rows = db.execute(
        "SELECT category, SUM(amount) AS total FROM expenses "
        "WHERE user_id = ? GROUP BY category ORDER BY total DESC",
        (user_id,)
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
