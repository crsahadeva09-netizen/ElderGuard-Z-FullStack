
import sqlite3
from database import get_connection


def seed_database():
    connection = get_connection()

    try:
        customers = [
            (101, "Ravi Kumar", 2250.0),
            (102, "Priya Sharma", 30000.0)
        ]

        connection.executemany("""
            INSERT OR IGNORE INTO customers
            (customer_id, name, average_transaction_amount)
            VALUES (?, ?, ?)
        """, customers)

        transactions = [
            (101, 1500.0, "Local Grocery"),
            (101, 2000.0, "Electricity Provider"),
            (101, 2500.0, "Pharmacy"),
            (101, 3000.0, "Local Grocery"),
            (102, 20000.0, "Known Recipient A"),
            (102, 25000.0, "Known Recipient B"),
            (102, 30000.0, "Known Recipient A"),
            (102, 45000.0, "Known Recipient C")
        ]

        connection.executemany("""
            INSERT INTO transactions
            (customer_id, amount, recipient, risk_level, status)
            VALUES (?, ?, ?, 'PENDING', 'HISTORICAL')
        """, transactions)

        connection.commit()

        print("Synthetic data inserted successfully.")

    finally:
        connection.close()


if __name__ == "__main__":
    seed_database()
