# Copyright (c) 2025, Jignasha Chavda and contributors
# For license information, please see license.txt

import frappe
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
