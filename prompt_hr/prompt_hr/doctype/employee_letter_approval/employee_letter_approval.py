# Copyright (c) 2025, Jignasha Chavda and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document


class EmployeeLetterApproval(Document):
    # ? reason of reject is mandatory when rejected the applicant
    def before_save(self):
        if self.workflow_state in ["Rejected", "Level 1 Rejected"]:
            if not self.reason_for_rejection:
                frappe.throw("Please provide a Reason for Rejection before rejecting this document.")

        # Always update next approver on workflow change (or on any save)
        self.set_next_pending_approver()


    # -------------------------------
    #  SET NEXT APPROVER
    # -------------------------------
    def set_next_pending_approver(self):
        """
        Determine next approver based on workflow configuration:
        1. Get next role for this workflow_state
        2. Find first employee linked to any user having that role (newest Has Role entry first)
        3. Save in pending_approval_emp_code_and_name
        """

        # If no workflow state, clear field
        if not self.workflow_state:
            self.pending_approval_emp_code_and_name = None
            return

        # Use the workflow defined on the document if present, else fallback to specific workflow name
        workflow_name = "WORKFLOW-APPR-44224"

        # Find transition row(s) where this is current state
        transition = frappe.get_all(
            "Workflow Transition",
            filters={
                "parent": workflow_name,
                "state": self.workflow_state
            },
            fields=["next_state", "allowed"],
            order_by="idx asc"
        )
        print("transition", transition)

        if not transition:
            self.pending_approval_emp_code_and_name = None
            return

        next_role = transition[0].allowed
        if not next_role:
            self.pending_approval_emp_code_and_name = None
            return

        # Find first valid employee for the role (most recently assigned user with that role who has an Employee)
        next_emp = self.get_first_employee_for_role(next_role)
        print("next_emp", next_emp)

        if next_emp:
            self.pending_approval_emp_code_and_name = f"{next_emp['employee_id']} - {next_emp['employee_name']}"
        else:
            self.pending_approval_emp_code_and_name = None


    # -------------------------------
    #  UTILITY FUNCTIONS
    # -------------------------------
    def get_first_employee_for_role(self, role):
        """
        Returns first valid employee linked to a user having this role.
        Uses SQL to join Has Role -> Employee and picks the most recently created Has Role entry (ORDER BY hr.creation DESC).
        Returns dict: { "employee_id": ..., "employee_name": ... } or None
        """

        # Join Has Role with Employee on user_id and return the first match
        sql = """
            SELECT
                e.name AS employee_id,
                e.employee_name
            FROM `tabHas Role` hr
            JOIN `tabEmployee` e ON e.user_id = hr.parent
            WHERE hr.role = %s
            ORDER BY hr.creation DESC
            LIMIT 1
        """

        res = frappe.db.sql(sql, (role,), as_dict=True)

        if res:
            return {"employee_id": res[0].employee_id, "employee_name": res[0].employee_name}

        return None
