#!/usr/bin/python3
"""
services.py

This module is responsible for all the logic operations and validation of the user input, if the user put the input that it is not correct the program flags it out without crashing the whole system or ruin tables in SQLITE3
It contains classes each one with the feature of being able to create, read, update and update the data. The classes created are members, equipments, loans and reports  """

import re
import sqlite3
from datetime import date, timedelta

from models import Member, Equipment, Loan


class ValidationError(Exception):
    """Raised for any rule violation the CLI should show to the operator."""


EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")


# --------------------------------------------------------------------------- #
# Members
# --------------------------------------------------------------------------- #
class MemberService:
    def __init__(self, db):
        self.db = db

    def register(self, name: str, email: str, phone: str = "") -> Member:
        name = (name or "").strip()
        email = (email or "").strip().lower()

        if not name:
            raise ValidationError("Member name cannot be empty.")
        if not EMAIL_RE.match(email):
            raise ValidationError(f"'{email}' is not a valid email address.")
        if self.find_by_email(email) is not None:
            raise ValidationError(f"A member with email '{email}' is already registered.")

        cur = self.db.conn.cursor()
        cur.execute(
            "INSERT INTO members (name, email, phone, registered_on) VALUES (?, ?, ?, ?)",
            (name, email, phone.strip(), date.today().isoformat()),
        )
        self.db.conn.commit()
        return self.get(cur.lastrowid)

    def update(self, member_id: int, name: str = None, email: str = None,
               phone: str = None) -> Member:
        """Update any subset of a member's fields. Pass None to leave a field unchanged."""
        current = self.get(member_id)

        new_name = current.name if name is None else name.strip()
        new_phone = current.phone if phone is None else phone.strip()
        if email is None:
            new_email = current.email
        else:
            new_email = email.strip().lower()
            if not EMAIL_RE.match(new_email):
                raise ValidationError(f"'{new_email}' is not a valid email address.")
            existing = self.find_by_email(new_email)
            if existing is not None and existing.id != member_id:
                raise ValidationError(f"A member with email '{new_email}' already exists.")

        if not new_name:
            raise ValidationError("Member name cannot be empty.")

        self.db.conn.execute(
            "UPDATE members SET name = ?, email = ?, phone = ? WHERE id = ?",
            (new_name, new_email, new_phone, member_id),
        )
        self.db.conn.commit()
        return self.get(member_id)

    def get(self, member_id: int) -> Member:
        row = self.db.conn.execute("SELECT * FROM members WHERE id = ?", (member_id,)).fetchone()
        if row is None:
            raise ValidationError(f"No member with id {member_id}.")
        return Member.from_row(row)

    def find_by_email(self, email: str):
        row = self.db.conn.execute(
            "SELECT * FROM members WHERE email = ?", (email.strip().lower(),)
        ).fetchone()
        return Member.from_row(row) if row else None

    def list_all(self):
        rows = self.db.conn.execute("SELECT * FROM members ORDER BY id").fetchall()
        return [Member.from_row(r) for r in rows]

    def search(self, query: str):
        """Search by exact id (if query is numeric) or by name/email substring."""
        query = (query or "").strip()
        if not query:
            raise ValidationError("Search text cannot be empty.")
        if query.isdigit():
            row = self.db.conn.execute(
                "SELECT * FROM members WHERE id = ?", (int(query),)
            ).fetchone()
            return [Member.from_row(row)] if row else []
        rows = self.db.conn.execute(
            "SELECT * FROM members WHERE name LIKE ? OR email LIKE ? ORDER BY id",
            (f"%{query}%", f"%{query}%"),
        ).fetchall()
        return [Member.from_row(r) for r in rows]

    def delete(self, member_id: int) -> None:
        self.get(member_id)  # raises if missing
        total_loans = self.db.conn.execute(
            "SELECT COUNT(*) FROM loans WHERE member_id = ?", (member_id,)
        ).fetchone()[0]
        if total_loans:
            raise ValidationError(
                "Cannot remove a member with loan history (active or past). "
                "This keeps loan records consistent."
            )
        try:
            self.db.conn.execute("DELETE FROM members WHERE id = ?", (member_id,))
            self.db.conn.commit()
        except sqlite3.IntegrityError:
            raise ValidationError("Cannot remove this member: related records still reference it.")


# --------------------------------------------------------------------------- #
# Equipment
# --------------------------------------------------------------------------- #
class EquipmentService:
    VALID_STATUSES = ("available", "on_loan", "maintenance")

    def __init__(self, db):
        self.db = db

    def register(self, name: str, category: str, condition_notes: str = "") -> Equipment:
        name = (name or "").strip()
        category = (category or "").strip()
        if not name:
            raise ValidationError("Equipment name cannot be empty.")
        if not category:
            raise ValidationError("Equipment category cannot be empty.")

        cur = self.db.conn.cursor()
        cur.execute(
            "INSERT INTO equipment (name, category, status, condition_notes) "
            "VALUES (?, ?, 'available', ?)",
            (name, category, condition_notes.strip()),
        )
        self.db.conn.commit()
        return self.get(cur.lastrowid)

    def update(self, equipment_id: int, name: str = None, category: str = None,
               condition_notes: str = None) -> Equipment:
        """Update name/category/notes. Status changes go through set_status/set_maintenance
        since those carry their own loan-state validation."""
        current = self.get(equipment_id)
        new_name = current.name if name is None else name.strip()
        new_category = current.category if category is None else category.strip()
        new_notes = current.condition_notes if condition_notes is None else condition_notes.strip()

        if not new_name:
            raise ValidationError("Equipment name cannot be empty.")
        if not new_category:
            raise ValidationError("Equipment category cannot be empty.")

        self.db.conn.execute(
            "UPDATE equipment SET name = ?, category = ?, condition_notes = ? WHERE id = ?",
            (new_name, new_category, new_notes, equipment_id),
        )
        self.db.conn.commit()
        return self.get(equipment_id)

    def get(self, equipment_id: int) -> Equipment:
        row = self.db.conn.execute(
            "SELECT * FROM equipment WHERE id = ?", (equipment_id,)
        ).fetchone()
        if row is None:
            raise ValidationError(f"No equipment with id {equipment_id}.")
        return Equipment.from_row(row)

    def list_all(self, status: str = None):
        if status:
            rows = self.db.conn.execute(
                "SELECT * FROM equipment WHERE status = ? ORDER BY id", (status,)
            ).fetchall()
        else:
            rows = self.db.conn.execute("SELECT * FROM equipment ORDER BY id").fetchall()
        return [Equipment.from_row(r) for r in rows]

    def search(self, query: str):
        """Search by exact id (if query is numeric) or by name/category substring."""
        query = (query or "").strip()
        if not query:
            raise ValidationError("Search text cannot be empty.")
        if query.isdigit():
            row = self.db.conn.execute(
                "SELECT * FROM equipment WHERE id = ?", (int(query),)
            ).fetchone()
            return [Equipment.from_row(row)] if row else []
        rows = self.db.conn.execute(
            "SELECT * FROM equipment WHERE name LIKE ? OR category LIKE ? ORDER BY id",
            (f"%{query}%", f"%{query}%"),
        ).fetchall()
        return [Equipment.from_row(r) for r in rows]

    def set_status(self, equipment_id: int, status: str) -> None:
        if status not in self.VALID_STATUSES:
            raise ValidationError(f"Status must be one of {self.VALID_STATUSES}.")
        self.get(equipment_id)
        self.db.conn.execute(
            "UPDATE equipment SET status = ? WHERE id = ?", (status, equipment_id)
        )
        self.db.conn.commit()

    def set_maintenance(self, equipment_id: int, note: str = "") -> None:
        item = self.get(equipment_id)
        if item.status == "on_loan":
            raise ValidationError("Cannot send equipment to maintenance while it is on loan.")
        self.db.conn.execute(
            "UPDATE equipment SET status = 'maintenance', condition_notes = ? WHERE id = ?",
            (note.strip() or item.condition_notes, equipment_id),
        )
        self.db.conn.commit()

    def delete(self, equipment_id: int) -> None:
        item = self.get(equipment_id)
        if item.status == "on_loan":
            raise ValidationError("Cannot remove equipment that is currently on loan.")
        total_loans = self.db.conn.execute(
            "SELECT COUNT(*) FROM loans WHERE equipment_id = ?", (equipment_id,)
        ).fetchone()[0]
        if total_loans:
            raise ValidationError(
                "Cannot remove equipment with loan history (active or past). "
                "This keeps loan records consistent."
            )
        try:
            self.db.conn.execute("DELETE FROM equipment WHERE id = ?", (equipment_id,))
            self.db.conn.commit()
        except sqlite3.IntegrityError:
            raise ValidationError("Cannot remove this equipment: related records still reference it.")


# --------------------------------------------------------------------------- #
# Loans
# --------------------------------------------------------------------------- #
class LoanService:
    def __init__(self, db, member_service: MemberService, equipment_service: EquipmentService):
        self.db = db
        self.members = member_service
        self.equipment = equipment_service

    def create_loan(self, member_id: int, equipment_id: int, loan_days: int = 7) -> Loan:
        self.members.get(member_id)  # validates member exists
        item = self.equipment.get(equipment_id)  # validates equipment exists

        if not item.is_available:
            raise ValidationError(
                f"Equipment '{item.name}' is not available (status: {item.status})."
            )
        if loan_days <= 0:
            raise ValidationError("Loan duration must be at least 1 day.")

        loan_date = date.today()
        due_date = loan_date + timedelta(days=loan_days)

        cur = self.db.conn.cursor()
        cur.execute(
            "INSERT INTO loans (member_id, equipment_id, loan_date, due_date, status) "
            "VALUES (?, ?, ?, ?, 'active')",
            (member_id, equipment_id, loan_date.isoformat(), due_date.isoformat()),
        )
        self.equipment.set_status(equipment_id, "on_loan")
        self.db.conn.commit()
        return self.get(cur.lastrowid)

    def close_loan(self, loan_id: int) -> Loan:
        loan = self.get(loan_id)
        if loan.status != "active":
            raise ValidationError(f"Loan {loan_id} is already closed.")

        self.db.conn.execute(
            "UPDATE loans SET status = 'returned', return_date = ? WHERE id = ?",
            (date.today().isoformat(), loan_id),
        )
        self.equipment.set_status(loan.equipment_id, "available")
        self.db.conn.commit()
        return self.get(loan_id)

    def get(self, loan_id: int) -> Loan:
        row = self.db.conn.execute("SELECT * FROM loans WHERE id = ?", (loan_id,)).fetchone()
        if row is None:
            raise ValidationError(f"No loan with id {loan_id}.")
        return Loan.from_row(row)

    def list_all(self):
        rows = self.db.conn.execute("SELECT * FROM loans ORDER BY id").fetchall()
        return [Loan.from_row(r) for r in rows]

    def active_loans(self):
        return [loan for loan in self.list_all() if loan.status == "active"]

    def overdue_loans(self):
        return [loan for loan in self.active_loans() if loan.is_overdue]

    def loans_for_member(self, member_id: int):
        self.members.get(member_id)
        rows = self.db.conn.execute(
            "SELECT * FROM loans WHERE member_id = ? ORDER BY id", (member_id,)
        ).fetchall()
        return [Loan.from_row(r) for r in rows]


# --------------------------------------------------------------------------- #
# Reports
# --------------------------------------------------------------------------- #
class ReportService:
    def __init__(self, db):
        self.db = db

    def equipment_status_counts(self):
        """Report: equipment counts grouped by status (available / on_loan / maintenance)."""
        rows = self.db.conn.execute(
            "SELECT status, COUNT(*) AS n FROM equipment GROUP BY status"
        ).fetchall()
        return {r["status"]: r["n"] for r in rows}

    def equipment_by_category(self):
        """Report: equipment grouped by category, with an availability breakdown."""
        rows = self.db.conn.execute(
            """
            SELECT category,
                   COUNT(*) AS total,
                   SUM(CASE WHEN status = 'available' THEN 1 ELSE 0 END) AS available
            FROM equipment
            GROUP BY category
            ORDER BY category
            """
        ).fetchall()
        return rows

    def most_borrowed_equipment(self, limit: int = 5):
        """Report: which equipment has been borrowed the most times."""
        rows = self.db.conn.execute(
            """
            SELECT e.id, e.name, COUNT(l.id) AS times_borrowed
            FROM equipment e
            JOIN loans l ON l.equipment_id = e.id
            GROUP BY e.id
            ORDER BY times_borrowed DESC, e.name
            LIMIT ?
            """,
            (limit,),
        ).fetchall()
        return rows

    def member_loan_summary(self):
        """Report: per-member total and active loan counts (member loan history overview)."""
        rows = self.db.conn.execute(
            """
            SELECT m.id, m.name,
                   COUNT(l.id) AS total_loans,
                   SUM(CASE WHEN l.status = 'active' THEN 1 ELSE 0 END) AS active_loans
            FROM members m
            LEFT JOIN loans l ON l.member_id = m.id
            GROUP BY m.id
            ORDER BY m.id
            """
        ).fetchall()
        return rows
