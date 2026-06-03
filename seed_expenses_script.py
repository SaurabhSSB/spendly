import sys
import random
from datetime import datetime, timedelta

sys.path.insert(0, '.')
from database.db import get_db

# Parse arguments
user_id = 1
count = 36
months = 10

# Category definitions: (name, min_amount, max_amount, weight)
# weight determines probability of selection
CATEGORIES = [
    ('Food', 50, 800, 5),
    ('Transport', 20, 500, 2),
    ('Bills', 200, 3000, 2),
    ('Health', 100, 2000, 1),
    ('Entertainment', 100, 1500, 1),
    ('Shopping', 200, 5000, 2),
    ('Other', 50, 1000, 1),
]

# Realistic Indian descriptions
DESCRIPTIONS = {
    'Food': [
        'Coffee and breakfast',
        'Lunch at office',
        'Grocery shopping',
        'Restaurant dinner',
        'Street food snacks',
        'Milk and bread',
        'Fruits and vegetables',
        'Bakery items',
    ],
    'Transport': [
        'Auto/Cab fare',
        'Bus pass',
        'Fuel for bike',
        'Train ticket',
        'Parking fee',
        'Auto to work',
    ],
    'Bills': [
        'Electricity bill',
        'Water bill',
        'Internet bill',
        'Mobile recharge',
        'Rent payment',
        'Insurance premium',
    ],
    'Health': [
        'Pharmacy medicines',
        'Doctor visit',
        'Dental checkup',
        'Vitamins and supplements',
        'Gym membership',
    ],
    'Entertainment': [
        'Movie tickets',
        'OTT subscription',
        'Gaming purchase',
        'Concert tickets',
        'Book purchase',
    ],
    'Shopping': [
        'Clothing',
        'Shoes',
        'Home decor',
        'Electronics',
        'Accessories',
    ],
    'Other': [
        'Miscellaneous',
        'Stationery',
        'Gifts',
        'Charity',
        'Repairs',
    ],
}

def get_random_date(months):
    """Generate a random date within the past N months."""
    today = datetime.now()
    days_back = random.randint(0, months * 30)
    return (today - timedelta(days=days_back)).strftime('%Y-%m-%d')

def generate_expenses(user_id, count, months):
    """Generate realistic expenses and insert them."""
    db = get_db()

    try:
        expenses = []
        dates = []

        # Build weighted category list
        category_pool = []
        for cat_name, min_amt, max_amt, weight in CATEGORIES:
            category_pool.extend([cat_name] * weight)

        for _ in range(count):
            category = random.choice(category_pool)
            cat_info = next(c for c in CATEGORIES if c[0] == category)
            amount = round(random.uniform(cat_info[1], cat_info[2]), 2)
            description = random.choice(DESCRIPTIONS[category])
            date = get_random_date(months)
            dates.append(date)

            expenses.append((user_id, amount, category, date, description))

        # Insert all expenses in a single transaction
        db.executemany(
            'INSERT INTO expenses (user_id, amount, category, date, description) VALUES (?, ?, ?, ?, ?)',
            expenses
        )
        db.commit()

        # Fetch inserted records for confirmation
        inserted = db.execute(
            'SELECT id, amount, category, date, description FROM expenses WHERE user_id = ? ORDER BY date DESC LIMIT 5',
            (user_id,)
        ).fetchall()

        # Print confirmation
        dates_sorted = sorted(dates)
        print(f"[OK] {count} expenses inserted for user {user_id}")
        print(f"Date range: {dates_sorted[0]} to {dates_sorted[-1]}")
        print(f"\nSample of 5 most recent records:")
        print(f"{'ID':<5} {'Amount':<10} {'Category':<15} {'Date':<12} {'Description':<30}")
        print("-" * 75)
        for row in inserted:
            print(f"{row[0]:<5} Rs {row[1]:<8.2f} {row[2]:<15} {row[3]:<12} {row[4]:<30}")

        db.close()

    except Exception as e:
        try:
            db.rollback()
        except:
            pass
        db.close()
        print(f"Error inserting expenses: {e}")
        sys.exit(1)

if __name__ == '__main__':
    generate_expenses(user_id, count, months)
