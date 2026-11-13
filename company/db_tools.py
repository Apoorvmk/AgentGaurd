"""Company database operations. Credentials stay inside the database layer."""
from database import get_connection

ALLOWED_TABLES = {"customers", "invoices"}


def read_record(table: str, record_id: int):
    if table not in ALLOWED_TABLES:
        raise ValueError("Table is not available")
    conn = get_connection("acmecorp")
    cursor = conn.cursor(dictionary=True)
    try:
        # Table identifiers are selected from a fixed allowlist; values are bound.
        cursor.execute(f"SELECT * FROM `{table}` WHERE id = %s", (record_id,))
        return cursor.fetchone()
    finally:
        cursor.close()
        conn.close()
