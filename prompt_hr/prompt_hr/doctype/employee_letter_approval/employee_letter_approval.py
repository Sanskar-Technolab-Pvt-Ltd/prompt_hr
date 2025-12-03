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
