#!/usr/bin/env python3
"""
main.py

Entry point and menu loop for the Campus MakerSpace Checkout System.
Run with: ./main.py   (or: python3 main.py)
Data persists in makerspace.db in the current directory between runs.

This module is intentionally "thin": it only handles input()/print() and
routes choices to the service layer (services.py). All validation and
database logic lives there, and raises ValidationError on any invalid
action, so nothing here can crash the program on bad input.
"""

from database import Database
from services import MemberService, EquipmentService, LoanService, ReportService, ValidationError


MAIN_MENU = """
==================== Campus MakerSpace Checkout ====================
 1. Register member
 2. Update member
 3. Register equipment
 4. Update equipment
 5. Create loan (check out equipment)
 6. Return loan (check in equipment)
 7. List members
 8. List equipment
 9. List loans
10. Search members
11. Search equipment
12. Reports
13. Send equipment to maintenance / back to available
14. Delete member
15. Delete equipment
 0. Exit
=======================================================================
"""

REPORTS_MENU = """
--------------------------- Reports ---------------------------
 1. Currently borrowed (active) loans
 2. Overdue loans
 3. Equipment status counts
 4. Equipment by category
 5. Most borrowed equipment
 6. Member loan summary
 7. Loan history for one member
 0. Back
-----------------------------------------------------------------
"""


class MakerSpaceApp:
    def __init__(self, db_path: str = "makerspace.db"):
        self.db = Database(db_path)
        self.members = MemberService(self.db)
        self.equipment = EquipmentService(self.db)
        self.loans = LoanService(self.db, self.members, self.equipment)
        self.reports = ReportService(self.db)

    # ------------------------------------------------------------------ #
    # Main loop
    # ------------------------------------------------------------------ #
    def run(self) -> None:
        print("Welcome to the Campus MakerSpace Checkout System.")
        actions = {
            "1": self.register_member,
            "2": self.update_member,
            "3": self.register_equipment,
            "4": self.update_equipment,
            "5": self.create_loan,
            "6": self.close_loan,
            "7": self.list_members,
            "8": self.list_equipment,
            "9": self.list_loans,
            "10": self.search_members,
            "11": self.search_equipment,
            "12": self.reports_menu,
            "13": self.maintenance_toggle,
            "14": self.delete_member,
            "15": self.delete_equipment,
        }
        while True:
            print(MAIN_MENU)
            choice = input("Choose an option: ").strip()
            if choice == "0":
                print("Goodbye.")
                break
            action = actions.get(choice)
            if action is None:
                print("Invalid option, try again.")
                continue
            try:
                action()
            except ValidationError as e:
                print(f"\n!! {e}")
        self.db.close()

    # ------------------------------------------------------------------ #
    # Members
    # ------------------------------------------------------------------ #
    def register_member(self):
        print("\n-- Register member --")
        name = input("Name: ")
        email = input("Email: ")
        phone = input("Phone (optional): ")
        member = self.members.register(name, email, phone)
        print(f"Registered: {member}")

    def update_member(self):
        print("\n-- Update member --")
        member_id = self._read_int("Member id: ")
        current = self.members.get(member_id)
        print(f"Current: {current}")
        print("Leave a field blank to keep its current value.")
        name = input(f"Name [{current.name}]: ").strip() or None
        email = input(f"Email [{current.email}]: ").strip() or None
        phone = input(f"Phone [{current.phone or '-'}]: ").strip() or None
        updated = self.members.update(member_id, name=name, email=email, phone=phone)
        print(f"Updated: {updated}")

    def list_members(self):
        print("\n-- Members --")
        self._print_list(self.members.list_all())

    def search_members(self):
        print("\n-- Search members --")
        query = input("Search by id, name, or email: ")
        self._print_list(self.members.search(query), empty="(no matches)")

    def delete_member(self):
        print("\n-- Delete member --")
        member_id = self._read_int("Member id: ")
        member = self.members.get(member_id)
        confirm = input(f"Delete {member}? This cannot be undone. Type 'yes' to confirm: ")
        if confirm.strip().lower() != "yes":
            print("Cancelled.")
            return
        self.members.delete(member_id)
        print(f"Member {member_id} deleted.")

    # ------------------------------------------------------------------ #
    # Equipment
    # ------------------------------------------------------------------ #
    def register_equipment(self):
        print("\n-- Register equipment --")
        name = input("Name (e.g. 'Canon EOS 90D'): ")
        category = input("Category (e.g. camera, laptop, soldering kit): ")
        notes = input("Condition notes (optional): ")
        item = self.equipment.register(name, category, notes)
        print(f"Registered: {item}")

    def update_equipment(self):
        print("\n-- Update equipment --")
        equipment_id = self._read_int("Equipment id: ")
        current = self.equipment.get(equipment_id)
        print(f"Current: {current}")
        print("Leave a field blank to keep its current value. (Status is changed via option 13.)")
        name = input(f"Name [{current.name}]: ").strip() or None
        category = input(f"Category [{current.category}]: ").strip() or None
        notes = input(f"Condition notes [{current.condition_notes or '-'}]: ").strip() or None
        updated = self.equipment.update(equipment_id, name=name, category=category,
                                         condition_notes=notes)
        print(f"Updated: {updated}")

    def list_equipment(self):
        print("\n-- Equipment --")
        filt = input("Filter by status (available/on_loan/maintenance, blank = all): ").strip()
        self._print_list(self.equipment.list_all(filt or None))

    def search_equipment(self):
        print("\n-- Search equipment --")
        query = input("Search by id, name, or category: ")
        self._print_list(self.equipment.search(query), empty="(no matches)")

    def delete_equipment(self):
        print("\n-- Delete equipment --")
        equipment_id = self._read_int("Equipment id: ")
        item = self.equipment.get(equipment_id)
        confirm = input(f"Delete {item}? This cannot be undone. Type 'yes' to confirm: ")
        if confirm.strip().lower() != "yes":
            print("Cancelled.")
            return
        self.equipment.delete(equipment_id)
        print(f"Equipment {equipment_id} deleted.")

    def maintenance_toggle(self):
        print("\n-- Maintenance --")
        equipment_id = self._read_int("Equipment id: ")
        item = self.equipment.get(equipment_id)
        print(f"Current: {item}")
        if item.status == "maintenance":
            self.equipment.set_status(equipment_id, "available")
            print("Marked as available.")
        else:
            note = input("Maintenance note (optional): ")
            self.equipment.set_maintenance(equipment_id, note)
            print("Marked as under maintenance.")

    # ------------------------------------------------------------------ #
    # Loans
    # ------------------------------------------------------------------ #
    def create_loan(self):
        print("\n-- Create loan (check out equipment) --")
        member_id = self._read_int("Member id: ")
        equipment_id = self._read_int("Equipment id: ")
        days = self._read_int("Loan duration in days (default 7): ", default=7)
        loan = self.loans.create_loan(member_id, equipment_id, days)
        print(f"Loan created: {loan}")

    def close_loan(self):
        print("\n-- Return loan (check in equipment) --")
        loan_id = self._read_int("Loan id: ")
        loan = self.loans.close_loan(loan_id)
        print(f"Loan closed: {loan}")

    def list_loans(self):
        print("\n-- Loans --")
        self._print_list(self.loans.list_all())

    # ------------------------------------------------------------------ #
    # Reports
    # ------------------------------------------------------------------ #
    def reports_menu(self):
        while True:
            print(REPORTS_MENU)
            choice = input("Choose a report: ").strip()
            if choice == "0":
                return
            elif choice == "1":
                self._print_list(self.loans.active_loans(), title="Currently borrowed")
            elif choice == "2":
                self._print_list(self.loans.overdue_loans(), title="Overdue loans")
            elif choice == "3":
                counts = self.reports.equipment_status_counts()
                print("\n-- Equipment status counts --")
                for status, n in counts.items():
                    print(f"  {status}: {n}")
            elif choice == "4":
                print("\n-- Equipment by category --")
                for row in self.reports.equipment_by_category():
                    print(f"  {row['category']}: {row['available']} available / {row['total']} total")
            elif choice == "5":
                print("\n-- Most borrowed equipment --")
                for row in self.reports.most_borrowed_equipment():
                    print(f"  [{row['id']}] {row['name']}: {row['times_borrowed']} loan(s)")
            elif choice == "6":
                print("\n-- Member loan summary --")
                for row in self.reports.member_loan_summary():
                    print(f"  [{row['id']}] {row['name']}: "
                          f"{row['total_loans']} total, {row['active_loans']} active")
            elif choice == "7":
                member_id = self._read_int("Member id: ")
                loans = self.loans.loans_for_member(member_id)
                self._print_list(loans, title=f"Loan history for member {member_id}")
            else:
                print("Invalid option, try again.")

    # ------------------------------------------------------------------ #
    # Helpers
    # ------------------------------------------------------------------ #
    @staticmethod
    def _print_list(items, title=None, empty="(none)"):
        if title:
            print(f"\n-- {title} --")
        if not items:
            print(empty)
        for item in items:
            print(item)

    @staticmethod
    def _read_int(prompt, default=None):
        raw = input(prompt).strip()
        if not raw and default is not None:
            return default
        try:
            return int(raw)
        except ValueError:
            raise ValidationError(f"'{raw}' is not a valid whole number.")


def main():
    app = MakerSpaceApp("makerspace.db")
    app.run()


if __name__ == "__main__":
    main()

