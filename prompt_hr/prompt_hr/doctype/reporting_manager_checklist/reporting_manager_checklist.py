# Copyright (c) 2025, Jignasha Chavda and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document


class ReportingManagerChecklist(Document):

    # ? FUNCTION TRIGGERED AFTER DOCUMENT IS SAVED
    def on_update(self):

       # ? SKIP RUNNING ON FIRST SAVE (CREATION)
        if self.flags.in_insert:
            return

        update_employee_onboarding_row(self)


# ? FUNCTION TO UPDATE EMPLOYEE ONBOARDING ACTIVITY ROW
def update_employee_onboarding_row(self):
    try:
        # ? GET ALL ROWS LINKED TO THIS CHECKLIST
        rows = frappe.get_all(
            "Employee Boarding Activity",
            filters={"custom_checklist_record": self.name},
            fields=["name", "user", "role"]
        )

        current_user = frappe.session.user
        user_roles = frappe.get_roles()

        matched_row = None

        for row in rows:
            if row.user == current_user:
                matched_row = row.name
                break
            if row.role and row.role in user_roles:
                matched_row = row.name
                break

        if matched_row:
            # ? UPDATE THE FIELD IF A MATCHING ROW IS FOUND
            frappe.db.set_value(
                "Employee Boarding Activity",
                matched_row,
                "custom_is_submitted",
                1
            )
            frappe.msgprint("Marked activity as submitted.")
        else:
            frappe.msgprint("No matching Employee Boarding Activity found for your user or role.")

    except Exception as e:
        frappe.msgprint("Something went wrong while updating onboarding activity.")
        frappe.log_error(frappe.get_traceback(), "Error in update_employee_onboarding_row")
