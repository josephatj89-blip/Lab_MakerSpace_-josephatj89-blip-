#!/usr/bin/python3
"""
models.py

Lightweight OOP wrappers around a single database row for each entity.
These carry no database logic themselves (that's the services' job) —
they just give the rest of the program typed objects instead of raw
sqlite3.Row tuples, plus a couple of convenience methods/properties.
"""

from datetime import date


class Member:
    def __init__(self, id, name, email, phone, registered_on):
        self.id = id
        self.name = name
        self.email = email
        self.phone = phone
        self.registered_on = registered_on

    def __str__(self):
        return f"[{self.id}] {self.name} <{self.email}> phone={self.phone or '-'}"

    @classmethod
    def from_row(cls, row):
        return cls(row["id"], row["name"], row["email"], row["phone"], row["registered_on"])


class Equipment:
    def __init__(self, id, name, category, status, condition_notes):
        self.id = id
        self.name = name
        self.category = category
        self.status = status
        self.condition_notes = condition_notes

    @property
    def is_available(self) -> bool:
        """True when this item can be loaned out right now."""
        return self.status == "available"

    def __str__(self):
        note = f" ({self.condition_notes})" if self.condition_notes else ""
        return f"[{self.id}] {self.name} | {self.category} | {self.status}{note}"

    @classmethod
    def from_row(cls, row):
        return cls(row["id"], row["name"], row["category"], row["status"], row["condition_notes"])


class Loan:
    def __init__(self, id, member_id, equipment_id, loan_date, due_date, return_date, status):
        self.id = id
        self.member_id = member_id
        self.equipment_id = equipment_id
        self.loan_date = loan_date
        self.due_date = due_date
        self.return_date = return_date
        self.status = status

    @property
    def is_overdue(self) -> bool:
        """Active loan whose due date has already passed."""
        if self.status != "active":
            return False
        return date.fromisoformat(self.due_date) < date.today()

    def __str__(self):
        tag = " OVERDUE" if self.is_overdue else ""
        ret = self.return_date or "-"
        return (f"[Loan {self.id}] member={self.member_id} equipment={self.equipment_id} "
                f"loaned={self.loan_date} due={self.due_date} returned={ret} "
                f"status={self.status}{tag}")

    @classmethod
    def from_row(cls, row):
        return cls(row["id"], row["member_id"], row["equipment_id"], row["loan_date"],
                    row["due_date"], row["return_date"], row["status"])
