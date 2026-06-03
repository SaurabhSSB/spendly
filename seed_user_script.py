import sys
import random
from datetime import datetime
from werkzeug.security import generate_password_hash

sys.path.insert(0, '/c/Users/hp/Desktop/claude_code/expense-tracker')
from database.db import get_db

# Indian names across regions
FIRST_NAMES = [
    'Rahul', 'Priya', 'Arjun', 'Neha', 'Rohan', 'Anjali', 'Vikram', 'Deepa',
    'Arun', 'Pooja', 'Sanjay', 'Kavya', 'Nikhil', 'Riya', 'Karan', 'Divya',
    'Aditya', 'Shreya', 'Varun', 'Ananya', 'Ashok', 'Priyanka', 'Manoj', 'Neetu',
    'Rajesh', 'Sneha', 'Harish', 'Nisha', 'Amit', 'Isha', 'Suresh', 'Meera'
]

LAST_NAMES = [
    'Sharma', 'Patel', 'Singh', 'Gupta', 'Kumar', 'Verma', 'Rao', 'Nair',
    'Desai', 'Iyer', 'Menon', 'Pandey', 'Mishra', 'Malhotra', 'Khanna', 'Bhat',
    'Reddy', 'Chatterjee', 'Banerjee', 'Das', 'Roy', 'Mukherjee', 'Sinha', 'Joshi',
    'Tripathi', 'Saxena', 'Chopra', 'Bhardwaj', 'Agarwal', 'Tiwari', 'Kapoor', 'Mathur'
]

def generate_unique_user():
    """Generate a unique user with random Indian name and email."""
    db = get_db()

    while True:
        first_name = random.choice(FIRST_NAMES)
        last_name = random.choice(LAST_NAMES)
        name = f"{first_name} {last_name}"

        email_base = f"{first_name.lower()}.{last_name.lower()}"
        email_suffix = random.randint(10, 999)
        email = f"{email_base}{email_suffix}@gmail.com"

        # Check if email already exists
        row = db.execute('SELECT id FROM users WHERE email = ?', (email,)).fetchone()
        if row is None:
            db.close()
            return name, email

    db.close()

def seed_single_user():
    """Seed a single Indian user into the database."""
    name, email = generate_unique_user()
    password_hash = generate_password_hash('password123')
    created_at = datetime.now().isoformat()

    db = get_db()
    db.execute(
        'INSERT INTO users (name, email, password_hash, created_at) VALUES (?, ?, ?, ?)',
        (name, email, password_hash, created_at)
    )
    db.commit()

    user_id = db.execute('SELECT last_insert_rowid()').fetchone()[0]
    db.close()

    # Print confirmation
    print(f"User created successfully!")
    print(f"ID:    {user_id}")
    print(f"Name:  {name}")
    print(f"Email: {email}")

if __name__ == '__main__':
    seed_single_user()
