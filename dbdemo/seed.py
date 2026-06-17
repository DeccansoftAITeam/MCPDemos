#!/usr/bin/env python3
"""Create a small SQLite database (store.db) for the Database Tool Server lab.

Run once before db_server.py:  python seed_db.py
"""
import os
import sqlite3
from pathlib import Path

DB_PATH = Path(os.environ.get("DB_PATH", "./store.db")).resolve()

conn = sqlite3.connect(DB_PATH)
conn.executescript(
    """
    DROP TABLE IF EXISTS orders;
    DROP TABLE IF EXISTS products;

    CREATE TABLE products (
        id       INTEGER PRIMARY KEY,
        name     TEXT NOT NULL,
        category TEXT,
        price    REAL
    );

    CREATE TABLE orders (
        id          INTEGER PRIMARY KEY,
        product_id  INTEGER REFERENCES products(id),
        qty         INTEGER,
        customer    TEXT
    );

    INSERT INTO products (name, category, price) VALUES
        ('Widget', 'hardware', 9.99),
        ('Gadget', 'hardware', 19.99),
        ('Manual', 'docs', 0.0);

    INSERT INTO orders (product_id, qty, customer) VALUES
        (1, 3, 'alice'),
        (2, 1, 'bob'),
        (1, 5, 'carol');
    """
)
conn.commit()
conn.close()
print(f"Seeded database at {DB_PATH}")
