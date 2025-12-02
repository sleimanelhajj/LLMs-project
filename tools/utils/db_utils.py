"""
Database utilities and connection helpers.
"""

import sqlite3
from config import CATALOG_DB_PATH


def get_db_connection():
    """Get a database connection with row factory."""
    conn = sqlite3.connect(CATALOG_DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn
