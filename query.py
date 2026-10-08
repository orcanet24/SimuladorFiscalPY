#!/usr/bin/env python3
"""
query.py - Query functions for the fiscal printer docs database.
Usage:
    python query.py commands <brand> <model>
    python query.py command_detail <cmd_name>
    python query.py status_codes <brand> <model> <type>
    python query.py response <cmd_name>
    python query.py models
"""

import sqlite3
import os
import json
import sys

DB_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "docs.db")


def get_connection(db_path: str = DB_PATH) -> sqlite3.Connection:
    """Get a connection to the database."""
    if not os.path.exists(db_path):
        print(f"Database not found at {db_path}. Run create_database.py and populate_database.py first.")
        sys.exit(1)
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    return conn


def get_all_commands_for_model(conn, brand: str = None, model: str = None) -> list:
    """
    Get all commands for a given printer model.
    Returns list of commands with their parameters and response formats.
    """
    cursor = conn.cursor()
    query = """
        SELECT
            c.id, c.cmd_name, c.syntax, c.description, c.param_count, c.category,
            pm.brand, pm.model, pm.identifier_string, pm.dll_name, pm.protocol_type
        FROM commands c
        JOIN printer_models pm ON c.model_id = pm.id
    """
    params = []
    conditions = []
    if brand:
        conditions.append("pm.brand LIKE ?")
        params.append(f"%{brand}%")
    if model:
        conditions.append("pm.model LIKE ?")
        params.append(f"%{model}%")

    if conditions:
        query += " WHERE " + " AND ".join(conditions)

    query += " ORDER BY c.category, c.cmd_name"

    cursor.execute(query, params)
    commands = []
    for row in cursor.fetchall():
        cmd = dict(row)
        # Get parameters
        cursor.execute("""
            SELECT param_name, param_type, required, description, param_order
            FROM command_parameters
            WHERE command_id = ?
            ORDER BY param_order
        """, (cmd["id"],))
        cmd["parameters"] = [dict(r) for r in cursor.fetchall()]

        # Get response format
        cursor.execute("""
            SELECT field_name, field_type, field_order, description
            FROM response_formats
            WHERE model_id = (SELECT id FROM printer_models WHERE brand LIKE ? AND model LIKE ? LIMIT 1)
            AND cmd_name = ?
            ORDER BY field_order
        """, (f"%{brand}%" if brand else "%", f"%{model}%" if model else "%", cmd["cmd_name"]))
        cmd["response_format"] = [dict(r) for r in cursor.fetchall()]

        commands.append(cmd)

    return commands


def get_command_detail(conn, cmd_name: str) -> list:
    """Get detailed info about a specific command across all models."""
    cursor = conn.cursor()
    cursor.execute("""
        SELECT c.*, pm.brand, pm.model
        FROM commands c
        JOIN printer_models pm ON c.model_id = pm.id
        WHERE c.cmd_name = ?
    """, (cmd_name,))
    results = []
    for row in cursor.fetchall():
        cmd = dict(row)
        cursor.execute("""
            SELECT param_name, param_type, required, description, param_order
            FROM command_parameters
            WHERE command_id = ?
            ORDER BY param_order
        """, (cmd["id"],))
        cmd["parameters"] = [dict(r) for r in cursor.fetchall()]
        results.append(cmd)
    return results


def get_status_codes(conn, brand: str = None, model: str = None, status_type: str = None) -> list:
    """Get status codes, optionally filtered by brand/model/type."""
    cursor = conn.cursor()
    query = """
        SELECT sc.*, pm.brand, pm.model
        FROM status_codes sc
        JOIN printer_models pm ON sc.model_id = pm.id
    """
    params = []
    conditions = []
    if brand:
        conditions.append("pm.brand LIKE ?")
        params.append(f"%{brand}%")
    if model:
        conditions.append("pm.model LIKE ?")
        params.append(f"%{model}%")
    if status_type:
        conditions.append("sc.status_type = ?")
        params.append(status_type)

    if conditions:
        query += " WHERE " + " AND ".join(conditions)

    query += " ORDER BY sc.status_type, sc.code_bit"
    cursor.execute(query, params)
    return [dict(r) for r in cursor.fetchall()]


def get_response_format(conn, cmd_name: str, brand: str = None) -> list:
    """Get response format for a command."""
    cursor = conn.cursor()
    query = """
        SELECT rf.*, pm.brand, pm.model
        FROM response_formats rf
        JOIN printer_models pm ON rf.model_id = pm.id
        WHERE rf.cmd_name = ?
    """
    params = [cmd_name]
    if brand:
        query += " AND pm.brand LIKE ?"
        params.append(f"%{brand}%")
    query += " ORDER BY rf.field_order"
    cursor.execute(query, params)
    return [dict(r) for r in cursor.fetchall()]


def get_models(conn) -> list:
    """List all printer models."""
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM printer_models ORDER BY brand, model")
    return [dict(r) for r in cursor.fetchall()]


def search_commands(conn, search_term: str) -> list:
    """Search commands by name or description."""
    cursor = conn.cursor()
    cursor.execute("""
        SELECT c.cmd_name, c.syntax, c.description, c.category, pm.brand, pm.model
        FROM commands c
        JOIN printer_models pm ON c.model_id = pm.id
        WHERE c.cmd_name LIKE ? OR c.description LIKE ?
        ORDER BY pm.brand, c.cmd_name
    """, (f"%{search_term}%", f"%{search_term}%"))
    return [dict(r) for r in cursor.fetchall()]


def main():
    if len(sys.argv) < 2:
        print("Usage:")
        print("  python query.py commands <brand> <model>     - Get all commands for a model")
        print("  python query.py command_detail <cmd_name>    - Get details of a command")
        print("  python query.py status_codes [brand] [model] [type] - Get status codes")
        print("  python query.py response <cmd_name> [brand]  - Get response format")
        print("  python query.py models                       - List all models")
        print("  python query.py search <term>                - Search commands")
        sys.exit(0)

    conn = get_connection()
    action = sys.argv[1]

    if action == "commands":
        if len(sys.argv) < 4:
            print("Usage: python query.py commands <brand> <model>")
            sys.exit(1)
        brand = sys.argv[2]
        model = sys.argv[3]
        results = get_all_commands_for_model(conn, brand, model)
        print(json.dumps(results, indent=2, ensure_ascii=False))

    elif action == "command_detail":
        if len(sys.argv) < 3:
            print("Usage: python query.py command_detail <cmd_name>")
            sys.exit(1)
        cmd_name = sys.argv[2]
        results = get_command_detail(conn, cmd_name)
        print(json.dumps(results, indent=2, ensure_ascii=False))

    elif action == "status_codes":
        brand = sys.argv[2] if len(sys.argv) > 2 else None
        model = sys.argv[3] if len(sys.argv) > 3 else None
        stype = sys.argv[4] if len(sys.argv) > 4 else None
        results = get_status_codes(conn, brand, model, stype)
        print(json.dumps(results, indent=2, ensure_ascii=False))

    elif action == "response":
        if len(sys.argv) < 3:
            print("Usage: python query.py response <cmd_name> [brand]")
            sys.exit(1)
        cmd_name = sys.argv[2]
        brand = sys.argv[3] if len(sys.argv) > 3 else None
        results = get_response_format(conn, cmd_name, brand)
        print(json.dumps(results, indent=2, ensure_ascii=False))

    elif action == "models":
        results = get_models(conn)
        print(json.dumps(results, indent=2, ensure_ascii=False))

    elif action == "search":
        if len(sys.argv) < 3:
            print("Usage: python query.py search <term>")
            sys.exit(1)
        term = sys.argv[2]
        results = search_commands(conn, term)
        print(json.dumps(results, indent=2, ensure_ascii=False))

    else:
        print(f"Unknown action: {action}")
        sys.exit(1)

    conn.close()


if __name__ == "__main__":
    main()
