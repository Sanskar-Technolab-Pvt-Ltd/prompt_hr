# Copyright (c) 2025, Jignasha Chavda and contributors
# For license information, please see license.txt

import frappe
import json
from frappe.model.document import Document


class EmployeePenalty(Document):
    pass


@frappe.whitelist()
def cancel_penalties(ids, reason = None):
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
    notification_doc = frappe.get_doc("Notification", "Employee Penalty Cancellation")

    penalties = frappe.get_all(
        "Employee Penalty",
        filters={"name": ["in", ids], "is_leave_balance_restore":0},
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
        if reason:
            frappe.db.set_value("Employee Penalty", {"attendance":row_name}, "cancellation_reason", reason)
        frappe.db.set_value(doctype, row_name, "custom_employee_penalty_id", None)
        if doctype == "Attendance":
            frappe.db.set_value("Attendance", row_name, "custom_penalty_applied", "")

        if notification_doc:
            try:
                #! FETCH PENALTY NAME AND EMPLOYEE NAME (WITHOUT get_doc)
                penalty_name, penalty_employee, penalty_date = frappe.db.get_value(
                    "Employee Penalty",
                    {"attendance": row_name},
                    ["name", "employee", "penalty_date"]
                )

                if penalty_employee:
                    emp_user_id = frappe.db.get_value("Employee", penalty_employee, "user_id")
                    reporting_manager = frappe.db.get_value("Employee", penalty_employee, "reports_to")
                    reporting_manager_user = (
                        frappe.db.get_value("Employee", reporting_manager, "user_id")
                        if reporting_manager else None
                    )

                    current_user = frappe.session.user
                    current_user_employee = (
                        frappe.db.get_value("Employee", {"user_id": current_user}, "name")
                        or current_user
                    )

                    if emp_user_id or reporting_manager_user:
                        email_recipients = []
                        if emp_user_id:
                            email_recipients.append(emp_user_id)
                        if reporting_manager_user and reporting_manager_user != emp_user_id:
                            email_recipients.append(reporting_manager_user)

                        subject = frappe.render_template(
                            notification_doc.subject,
                            {"penalty": penalty_name, "employee_name": penalty_employee}
                        )
                        message = frappe.render_template(
                            notification_doc.message,
                            {
                                "penalty": penalty_name,
                                "employee_name": penalty_employee,
                                "current_user": current_user_employee,
                                "reason": reason,
                                "penalty_date": penalty_date
                            }
                        )

                        frappe.sendmail(
                            recipients=email_recipients,
                            subject=subject,
                            message=message,
                            reference_doctype="Employee Penalty",
                            reference_name=penalty_name,
                        )
                
            except Exception as e:
                frappe.log_error(f"Error sending cancellation notification", str(e))
                continue

    # ? BULK DELETE LEAVE LEDGER ENTRIES
    if leave_entries_to_delete:
        frappe.db.delete("Leave Ledger Entry", {"name": ["in", leave_entries_to_delete]})

    frappe.db.commit()
    return True
