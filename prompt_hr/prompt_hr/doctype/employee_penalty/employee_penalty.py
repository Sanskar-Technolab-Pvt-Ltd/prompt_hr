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

    penalties = frappe.get_all(
        "Employee Penalty",
        filters={"name": ["in", ids]},
        fields=["name"],
        pluck="name"
    )

    child_table_data = frappe.get_all(
        "Employee Leave Penalty Details",
        filters={"parent": ["in", penalties]},
        fields=["name", "leave_ledger_entry"]
    )

    for data in child_table_data:
        if data.leave_ledger_entry:
            leave_entries_to_delete.append(data.leave_ledger_entry)
            penalty_leave_pairs.append(("Employee Leave Penalty Details", data.name))

    # ? SET 'leave_ledger_entry' TO NONE IN BULK
    for doctype, row_name in penalty_leave_pairs:
        frappe.db.set_value(doctype, row_name, "leave_ledger_entry", None)

    # ? BULK DELETE LEAVE LEDGER ENTRIES
    if leave_entries_to_delete:
        frappe.db.delete("Leave Ledger Entry", {"name": ["in", leave_entries_to_delete]})

    frappe.db.commit()
    return True
