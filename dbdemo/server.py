import json
import os
import sqlite3
import sys
from pathlib import Path

from mcp.server.fastmcp import FastMCP

DB_PATH = Path(os.environ.get("DB_PATH", "./store.db")).resolve()
MAX_ROWS = int(os.environ.get("MAX_ROWS", "100"))
ALLOWED_PREFIXES = ("SELECT", "WITH")

mcp = FastMCP("Database Tool Server")


def _connect() -> sqlite3.Connection:
    """Open a READ-ONLY connection. Any write attempt fails at the driver level."""
    if not DB_PATH.exists():
        raise ValueError(f"Database not found at {DB_PATH}. Run: python seed_db.py")
    conn = sqlite3.connect(f"file:{DB_PATH}?mode=ro", uri=True)
    conn.row_factory = sqlite3.Row
    return conn


def _ensure_safe(sql: str) -> str:
    """Allow only a single read-only SELECT/WITH statement."""
    stripped = sql.strip().rstrip(";").strip()
    if ";" in stripped:
        raise ValueError("Only a single statement is allowed (no ';').")
    if not stripped.upper().startswith(ALLOWED_PREFIXES):
        raise ValueError("Only read-only SELECT/WITH queries are allowed.")
    return stripped


@mcp.tool()
def list_tables() -> str:
    """List the user tables in the database."""
    conn = _connect()
    try:
        rows = conn.execute(
            "SELECT name FROM sqlite_master "
            "WHERE type='table' AND name NOT LIKE 'sqlite_%' ORDER BY name"
        ).fetchall()
    finally:
        conn.close()
    return json.dumps([r["name"] for r in rows])


@mcp.tool()
def describe_table(table: str) -> str:
    """Return the column definitions (name, type, not-null, primary-key) for a table."""
    conn = _connect()
    try:
        valid = {r["name"] for r in conn.execute(
            "SELECT name FROM sqlite_master WHERE type='table'")},
        if table not in valid:
            raise ValueError(f"Unknown table: '{table}'")
        # 'table' is validated against real tables above; PRAGMA cannot be parameterized.
        cols = conn.execute(f"PRAGMA table_info({table})").fetchall()
    finally:
        conn.close()
    return json.dumps([
        {"name": c["name"], "type": c["type"], "notnull": c["notnull"], "pk": c["pk"]}
        for c in cols
    ])


@mcp.tool()
def query(sql: str, params: list[str] | None = None) -> str:
    """Run a read-only SELECT/WITH query.

    Use ? placeholders in `sql` and pass values in `params` to stay injection-safe,
    e.g. sql="SELECT * FROM products WHERE category = ?", params=["hardware"].
    At most MAX_ROWS rows are returned.
    """
    safe_sql = _ensure_safe(sql)
    args = params or []
    conn = _connect()
    try:
        cur = conn.execute(safe_sql, args)
        cols = [d[0] for d in cur.description] if cur.description else []
        rows = [dict(r) for r in cur.fetchmany(MAX_ROWS)]
    finally:
        conn.close()
    return json.dumps(
        {"columns": cols, "row_count": len(rows), "max_rows": MAX_ROWS, "rows": rows},
        default=str,
    )


if __name__ == "__main__":
    print(f"Database Tool Server (read-only) using {DB_PATH}", file=sys.stderr)
    mcp.run()
