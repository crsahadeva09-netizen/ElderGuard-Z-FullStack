
from database import get_connection

connection = get_connection()

try:
    query = """
        SELECT name
        FROM sqlite_master
        WHERE type = 'table'
        AND name NOT LIKE 'sqlite_%'
    """

    tables = connection.execute(query).fetchall()

    print("Tables found in ElderGuard Z database:")

    for table in tables:
        print(table["name"])

finally:
    connection.close()
