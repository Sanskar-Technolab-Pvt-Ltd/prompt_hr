# Copyright (c) 2025, Jignasha Chavda and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document
from frappe.utils import nowdate


class EmployeeProfileChangesApprovalInterface(Document):

    # ? ON UPDATE EVENT CONTROLLER METHOD
    def on_update(self):
        # ? HANDLE APPROVAL LOGIC
        if self.approval_status == "Approved" and (
            self.changes_applicable_date == nowdate()
            or not self.changes_applicable_date
        ):
            # ? SET EFFECTIVE DATE IF NOT ALREADY SET
            if not self.changes_applicable_date:
                self.changes_applicable_date = nowdate()
                self.save(ignore_permissions=True)

            self.apply_changes_to_employee()

        # ? HANDLE REJECTION LOGIC
     

    # ? UPDATE EMPLOYEE MASTER WITH APPROVED CHANGES
    def apply_changes_to_employee(self):

        if not self.employee:
            return

        frappe.db.set_value(
            "Employee",
            self.employee,
            self.field_name,
            self.new_value,
            update_modified=False,
        )

        frappe.msgprint(f"Approved changes applied to Employee {self.employee}")

    # ? SYNC ORIGINAL VALUES FROM EMPLOYEE TO EMPLOYEE PROFILE ON REJECTION
    def sync_data_from_employee(self):
        if not self.employee or not self.employee_profile_id:
            return

        employee = frappe.get_doc("Employee", self.employee)
        self.sync_employee_to_profile(employee)

        frappe.msgprint(
            f"Rejected changes. Reverted Employee Profile for {self.employee}"
        )

 