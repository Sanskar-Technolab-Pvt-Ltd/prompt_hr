# Copyright (c) 2025, Jignasha Chavda and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document

class ReportingManagerChecklist(Document):

	# ? FUNCTION TRIGGERED AFTER DOCUMENT IS SAVED
	def on_update(self):
		update_employee_onboarding_row(self)

	
# ? FUNCTION TO UPDATE EMPLOYEE ONBOARDING ACTIVITY ROW
def update_employee_onboarding_row(self):
    try:
        # ? CHECK IF A MATCHING EMPLOYEE BOARDING ACTIVITY ROW EXISTS
        row_name = frappe.db.exists(
            "Employee Boarding Activity",
            {
                "custom_checklist_record": self.name,
                "user": frappe.session.user
            }
        )

        if row_name:
            # ? UPDATE THE FIELD IF ROW EXISTS
            frappe.db.set_value(
                "Employee Boarding Activity",
                row_name, 
                "custom_is_submitted",
                1
            )
            frappe.msgprint(f"Marked activity as submitted.")
        else:
            frappe.msgprint("No matching Employee Boarding Activity found.")
    except Exception as e:
        frappe.msgprint("Something went wrong while updating onboarding activity.")
        frappe.log_error(frappe.get_traceback(), "Error in update_employee_onboarding_row")

