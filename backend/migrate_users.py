
import sqlite3
from database import get_connection

connection = get_connection()

try:
    columns = connection.execute(
        "PRAGMA table_info(users)"
    ).fetchall()

    column_names = [column[1] for column in columns]

    if not column_names:
        raise RuntimeError(
            "The users table was not found. "
            "Check that Flask and this script use the same database."
        )

    if "phone" in column_names:
        print("The phone column already exists. No changes needed.")
    else:
        connection.execute(
            "ALTER TABLE users ADD COLUMN phone TEXT"
        )
        connection.commit()
        print("Migration successful: phone column added.")

    updated_columns = connection.execute(
        "PRAGMA table_info(users)"
    ).fetchall()

    print("Current users table columns:")
    for column in updated_columns:
        print("-", column[1])

except Exception:
    connection.rollback()
    raise

finally:
    connection.close()
