# Copyright (c) 2025, Jignasha Chavda and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document


class ReportingManagerChecklist(Document):

    # ? FUNCTION TRIGGERED AFTER DOCUMENT IS SAVED
    def on_update(self):

        # ! DO NOT RUN THIS LOGIC IF DOCUMENT IS BEING CREATED FOR THE FIRST TIME
        if self.is_new():
            return

        # ? RUN ONBOARDING ROW UPDATE LOGIC ONLY ON UPDATE
        update_employee_onboarding_rows(self)


# ? FUNCTION TO UPDATE ALL MATCHING EMPLOYEE ONBOARDING ACTIVITY ROWS
def update_employee_onboarding_rows(self):
    try:
        # ? FETCH CURRENT USER AND THEIR ROLES
        current_user = frappe.session.user
        user_roles = frappe.get_roles(current_user)

        # ? GET ALL EMPLOYEE BOARDING ACTIVITY RECORDS LINKED TO THIS CHECKLIST
        potential_rows = frappe.get_all(
            "Employee Boarding Activity",
            filters={"custom_checklist_record": self.name},
            fields=["name", "user", "role"],
        )

        # ? TRACK HOW MANY ROWS WERE UPDATED
        updated_rows = 0

        for row in potential_rows:
            # * CHECK IF ROW MATCHES CURRENT USER OR ANY ROLE
            if (row.user == current_user) or (row.role and row.role in user_roles):
                # ? UPDATE FIELD TO MARK AS SUBMITTED
                frappe.db.set_value(
                    "Employee Boarding Activity", row.name, "custom_is_submitted", 1
                )
                updated_rows += 1

        # ? SHOW MESSAGE BASED ON UPDATE RESULTS
        if updated_rows:
            frappe.msgprint(
                f"Marked {updated_rows} onboarding activity row(s) as submitted."
            )
        else:
            frappe.msgprint(
                "No matching Employee Boarding Activity rows found for your user or roles."
            )

    except Exception as e:
        # ! CATCH AND LOG EXCEPTION
        frappe.msgprint("Something went wrong while updating onboarding activities.")
        frappe.log_error(
            frappe.get_traceback(), "Error in update_employee_onboarding_rows"
        )
