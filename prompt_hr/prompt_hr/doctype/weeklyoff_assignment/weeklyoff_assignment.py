# Copyright (c) 2025, Jignasha Chavda and contributors
# For license information, please see license.txt

import frappe
from frappe import _
from frappe.model.document import Document
from prompt_hr.py.utils import send_notification_email

class WeeklyOffAssignment(Document):
	
	def on_submit(self):

		# * SENDING EMAIL TO EMPLOYEE
		emp_user = frappe.db.get_value("Employee", self.employee, "user_id")
		if emp_user:
			send_notification_email(
				recipients=[emp_user],
				notification_name="Weekly Off Assignment",
				doctype="WeeklyOff Assignment",
				docname=self.name,
				fallback_subject="Weekly Off Assignment",
				fallback_message="<p>Hi Employee,</p> <br> <p>Your weekly off has been assigned. Please take note and plan your work accordingly.</p>"
			)
   
	def on_update(self):
     
		employee_id = self.employee
    
		if not employee_id:
			return

		# Get the manager linked in Employee's custom_dotted_line_manager field
		manager_id = frappe.db.get_value("Employee", employee_id, "custom_dotted_line_manager")
		
		if not manager_id:
			return

		# Get the manager's user ID (needed for sharing the document)
		manager_user_id = frappe.db.get_value("Employee", manager_id, "user_id")
		
		if not manager_user_id:
			return

		# Check if the WeeklyOff Assignment is already shared with the manager
		existing_share = frappe.db.exists("DocShare", {
			"share_doctype": "WeeklyOff Assignment",
			"share_name": self.name,
			"user": manager_user_id
		})

		if existing_share:
			return

		# Share the WeeklyOff Assignment with manager (read-only)
		frappe.share.add_docshare(
			doctype="WeeklyOff Assignment",
			name=self.name,
			user=manager_user_id,
			read=1,      # Read permission
			write=0,
			share=0,
			flags={"ignore_share_permission": True}
		)


