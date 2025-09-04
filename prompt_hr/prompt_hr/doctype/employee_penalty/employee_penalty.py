# Copyright (c) 2025, Jignasha Chavda and contributors
# For license information, please see license.txt

import frappe
import json
from frappe.model.document import Document


class EmployeePenalty(Document):
    pass


@frappe.whitelist()
def cancel_penalties(ids):
    """Cancel penalties and delete linked leave ledger entries efficiently and securely."""

    if not ids:
        return

    # ? CONVERT TO PYTHON LIST IF IT'S A JSON STRING
    if isinstance(ids, str):
        try:
            ids = json.loads(ids)
        except Exception:
            ids = [ids]

    # ? GATHER ALL LEAVE LEDGER ENTRY IDS AND PENALTY-ROW PAIRS
    leave_entries_to_delete = []
    penalty_leave_pairs = []
    attendance_penalty_pairs = []

    penalties = frappe.get_all(
        "Employee Penalty",
        filters={"name": ["in", ids]},
        fields=["name", "attendance"],
    )

    child_table_data = frappe.get_all(
        "Employee Leave Penalty Details",
        filters={"parent": ["in", [p.name for p in penalties]]},
        fields=["name", "leave_ledger_entry"]
    )

    # ? HANDLE ATTENDANCE FIELD IN PARENT PENALTY
    for penalty in penalties:
        if penalty.attendance:
            attendance_penalty_pairs.append(("Attendance", penalty.attendance))

    # ? HANDLE CHILD TABLE LEAVE LEDGER ENTRIES
    for data in child_table_data:
        if data.leave_ledger_entry:
            leave_entries_to_delete.append(data.leave_ledger_entry)
            penalty_leave_pairs.append(("Employee Leave Penalty Details", data.name))

    # ? SET 'leave_ledger_entry' TO NONE IN CHILD TABLE
    for doctype, row_name in penalty_leave_pairs:
        frappe.db.set_value(doctype, row_name, "leave_ledger_entry", None)

    # ? UNLINK PENALTIES FROM ATTENDANCE
    for doctype, row_name in attendance_penalty_pairs:
        frappe.db.set_value("Employee Penalty", {"attendance":row_name}, "is_leave_balance_restore", 1)
        frappe.db.set_value(doctype, row_name, "custom_employee_penalty_id", None)

    # ? BULK DELETE LEAVE LEDGER ENTRIES
    if leave_entries_to_delete:
        frappe.db.delete("Leave Ledger Entry", {"name": ["in", leave_entries_to_delete]})

    frappe.db.commit()
    return True
