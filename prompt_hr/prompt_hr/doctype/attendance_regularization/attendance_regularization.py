# Copyright (c) 2025, Jignasha Chavda and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document
from prompt_hr.py.utils import send_notification_email, is_user_reporting_manager_or_hr
from frappe.utils import get_datetime, getdate
from prompt_hr.py.auto_mark_attendance import mark_attendance
from frappe.utils import get_datetime, add_days


class AttendanceRegularization(Document):
	
	def validate(self):
		
		is_rh = is_user_reporting_manager_or_hr(user_id=frappe.session.user, requesting_employee_id=self.employee)
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

	def before_save(self):
		if (self.regularization_date and self.employee) and not self.attendance:
			attendance_id = frappe.db.get_value(
				"Attendance",
				{"attendance_date": self.regularization_date, "employee": self.employee},
			)
			if attendance_id:
				self.attendance = attendance_id

		if not self.checkinpunch_details:
			frappe.throw("Checkin details not found", title="Data Missing")
		if self.get("status") in ["Approved", "Rejected"]:
			return

		attendance_regularization_limit = int(frappe.db.get_single_value("HR Settings", "custom_allowed_to_raise_regularizations_for_past_days_for_prompt") or 0)
		limit_date = add_days(frappe.utils.getdate(), -attendance_regularization_limit)

		

	
		# ! VALIDATE IF REGULARIZATION DATE IS WITHIN THE LIMIT
		if get_datetime(self.regularization_date).date() < limit_date:
			frappe.throw(f"Attendance Regularization cannot be raised for past dates more than {attendance_regularization_limit} days.")

		if self.get("attendance"):
			attendance_doc = frappe.get_doc("Attendance", self.attendance)
			# ! VALIDATE IF ATTENDANCE DATE IS WITHIN THE LIMIT
			if attendance_doc.attendance_date < limit_date:
				frappe.throw(f"Attendance Regularization cannot be raised for past dates more than {attendance_regularization_limit} days.")
