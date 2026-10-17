
from database import get_connection

connection = get_connection()

try:
    print("\nCUSTOMERS")

    customers = connection.execute("""
        SELECT customer_id, name, average_transaction_amount
        FROM customers
        ORDER BY customer_id
    """).fetchall()

    for customer in customers:
        print(dict(customer))

    print("\nTRANSACTIONS")

    transactions = connection.execute("""
        SELECT transaction_id, customer_id, amount, recipient, status
        FROM transactions
        ORDER BY transaction_id
    """).fetchall()

    for transaction in transactions:
        print(dict(transaction))

finally:
    connection.close()
