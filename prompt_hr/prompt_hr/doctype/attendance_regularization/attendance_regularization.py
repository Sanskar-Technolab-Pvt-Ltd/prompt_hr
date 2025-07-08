# Copyright (c) 2025, Jignasha Chavda and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document
from prompt_hr.py.utils import check_user_is_reporting_manager, send_notification_email
from frappe.utils import get_datetime, time_diff_in_hours
from prompt_hr.py.auto_mark_attendance import mark_attendance


class AttendanceRegularization(Document):
	
	def validate(self):
		
		is_rh = check_user_is_reporting_manager(user_id=frappe.session.user, requesting_employee_id=self.employee)
		if is_rh:
			if self.status == "Approved" :
				
				in_times = [get_datetime(f"{self.regularization_date} {row.in_time}") for row in self.checkinpunch_details if row.in_time]
				out_times = [get_datetime(f"{self.regularization_date} {row.out_time}") for row in self.checkinpunch_details if row.out_time]
    
				in_time = min(in_times) if in_times else None
				out_time = max(out_times) if out_times else None
    
				# * CODE FOR CALCULATING WORKING HOURS COMMENTED FOR NOW
				# working_hours = 0
				# last_in_time = None
	
				# for row in self.checkinpunch_details:
					
				# 	if row.in_time:
				# 		last_in_time = row.in_time

				# 	if row.out_time and last_in_time:
				# 		working_hours += time_diff_in_hours(row.out_time, last_in_time)
				
				# frappe.db.set_value("Attendance", self.attendance, {"in_time", ""})
				print(f"\n\n Calling Mark Attendance \n\n")
				mark_attendance(
					attendance_date = self.regularization_date,
					company=self.company,
					regularize_attendance = 1,
					attendance_id = self.attendance if self.attendance else None,
					regularize_start_time = in_time,
					regularize_end_time = out_time,
					emp_id=self.employee
				)
				# * --------------------------------------------------------------------------
				# attendance_doc = frappe.get_doc("Attendance", self.attendance)
				# attendance_doc.flags.ignore_validate_update_after_submit = True
				# attendance_doc.in_time = in_time
				# attendance_doc.out_time = out_time
				# # attendance_doc.working_hours = round(working_hours, 2)
				# attendance_doc.save(ignore_permissions=True)
				# *----------------------------------------------------------------------------------
				# * SENDING MAIL TO INFORM EMPLOYEE ABOUT ATTENDANCE REGULARIZATION IS APPROVED AND ONLY SENDING MAIL IF EMPLOYEE IS NOT NOTIFIED
				if not self.employee_notified:
					emp_user_id = frappe.db.get_value("Employee", self.employee, "user_id")
					if emp_user_id:
						send_notification_email(
													recipients=[emp_user_id],
													notification_name="Attendance Regularization Approved",
													doctype="Attendance Regularization",
													docname=self.name,
													send_link=True,
													fallback_subject=f"Attendance Regularization Approved for {self.regularization_date}",
													fallback_message=f"<p>Dear {self.employee_name},</p> <br> <p>This is to inform you that your Attendance Regularization request for {self.regularization_date} has been reviewed and approved.</p>"
												)
						self.employee_notified = 1

			if self.status == "Rejected" and not self.employee_notified:
				
				emp_user_id = frappe.db.get_value("Employee", self.employee, "user_id")
				if emp_user_id:
					send_notification_email(
													recipients=[emp_user_id],
													notification_name="Attendance Regularization Rejected",
													doctype="Attendance Regularization",
													docname=self.name,
													send_link=True,
													fallback_subject=f"Attendance Regularization Rejected for {self.regularization_date}",
													fallback_message=f"<p>Dear {self.employee_name},</p> <br> <p>This is to inform you that your Attendance Regularization request for {self.regularization_date} has been reviewed and has unfortunately been rejected.</p>"
												)
					self.employee_notified = 1

	def on_update(self):
		# Validate permission: Only Reporting Manager can modify the status
		is_reporting_manager = check_user_is_reporting_manager(
			user_id=frappe.session.user,
			requesting_employee_id=self.employee
		).get("is_rh")

		if not is_reporting_manager and self.status and self.has_value_changed("status"):
			frappe.throw("You are not permitted to update the status. Please contact the Reporting Manager.")

