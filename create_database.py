#!/usr/bin/env python3
"""
create_database.py - Creates the SQLite fiscal printer docs database.
Usage: python create_database.py
"""

import sqlite3
import os

DB_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "docs.db")
SCHEMA_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "schema.sql")


def create_database(db_path: str = DB_PATH, schema_path: str = SCHEMA_PATH) -> str:
    """Create the database and apply schema. Returns the db path."""
    if os.path.exists(db_path):
        os.remove(db_path)
        print(f"Removed existing database: {db_path}")

    with open(schema_path, "r", encoding="utf-8") as f:
        schema = f.read()

    conn = sqlite3.connect(db_path)
    conn.executescript(schema)
    conn.close()
    print(f"Database created at: {db_path}")
    return db_path


if __name__ == "__main__":
    create_database()
