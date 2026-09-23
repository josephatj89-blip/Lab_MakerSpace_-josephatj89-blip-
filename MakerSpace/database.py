#!/usr/bin/python3
"""
database.py

Owns the single SQLite connection and the schema. Every other module
talks to the database through a Database instance rather than opening
its own connection.
"""

import sqlite3
from pathlib import Path


class Database:
    """Wraps a SQLite connection and owns schema creation."""

    def __init__(self, db_path: str = "makerspace.db"):
        self.db_path = Path(db_path)
        self.conn = sqlite3.connect(self.db_path)
        self.conn.execute("PRAGMA foreign_keys = ON")
        self.conn.row_factory = sqlite3.Row
        self._create_schema()

    def _create_schema(self) -> None:
        cursor = self.conn.cursor()

        cursor.execute("""
            CREATE TABLE IF NOT EXISTS members (
                id             INTEGER PRIMARY KEY AUTOINCREMENT,
                name           TEXT NOT NULL,
                email          TEXT NOT NULL UNIQUE,
                phone          TEXT,
                registered_on  TEXT NOT NULL
            )
        """)

        cursor.execute("""
            CREATE TABLE IF NOT EXISTS equipment (
                id              INTEGER PRIMARY KEY AUTOINCREMENT,
                name            TEXT NOT NULL,
                category        TEXT NOT NULL,
                status          TEXT NOT NULL DEFAULT 'available'
                                CHECK (status IN ('available', 'on_loan', 'maintenance')),
                condition_notes TEXT DEFAULT ''
            )
        """)

        cursor.execute("""
            CREATE TABLE IF NOT EXISTS loans (
                id            INTEGER PRIMARY KEY AUTOINCREMENT,
                member_id     INTEGER NOT NULL,
                equipment_id  INTEGER NOT NULL,
                loan_date     TEXT NOT NULL,
                due_date      TEXT NOT NULL,
                return_date   TEXT,
                status        TEXT NOT NULL DEFAULT 'active'
                              CHECK (status IN ('active', 'returned')),
                FOREIGN KEY (member_id) REFERENCES members(id),
                FOREIGN KEY (equipment_id) REFERENCES equipment(id)
            )
        """)

        self.conn.commit()

    def close(self) -> None:
        self.conn.close()
