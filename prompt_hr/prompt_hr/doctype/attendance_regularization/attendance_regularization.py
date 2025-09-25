# Copyright (c) 2025, Jignasha Chavda and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document
from prompt_hr.py.utils import send_notification_email, is_user_reporting_manager_or_hr, get_reporting_manager_info
from frappe.utils import get_datetime, getdate, format_date, get_link_to_form
from prompt_hr.py.auto_mark_attendance import mark_attendance
from frappe.utils import get_datetime, add_days
from frappe import _
from prompt_hr.overrides.attendance_override import modify_employee_penalty

class AttendanceRegularization(Document):

	def before_insert(self):
		self.status = "Pending"
		self.auto_approve = 0
		self.employee_notified = 0
	
	def validate(self):

		# ? NOT ALLOW TO APPLY REGULARIZATION IN FUTURE DATES AND TODAY
		if get_datetime(self.regularization_date).date() >= getdate():
			frappe.throw("Attendance Regularization cannot be raised for future or current dates.")

		# ? VALIDATE OUT TIME CANNOT BE LESS THAN IN TIME IN CHILD TABLE
		validate_in_out_time(self)

		# ? CHECK IF ATTENDANCE REGULARIZATION ALREADY EXISTS FOR THE SAME DATE
		attendance_regularization_exists = frappe.get_all(
			"Attendance Regularization",
			filters={
				"employee": self.employee,
				"regularization_date": self.regularization_date,
				"name": ["!=", self.name],
				"workflow_state": ["!=", "Rejected"]
			},
			fields=["name"],
			limit=1
		)

		if attendance_regularization_exists:
			existing_name = attendance_regularization_exists[0].name
			frappe.throw(
				f"""
				Attendance Regularization already exists for
				<b>{self.employee}</b> on <b>{format_date(self.regularization_date)}</b>.<br>
				{get_link_to_form('Attendance Regularization', existing_name)}
				""",
				title="Duplicate Attendance Regularization"
			)
		
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
				try:
					modify_employee_penalty(self.employee, self.regularization_date)
				except Exception as e:
					frappe.log_error("Error in Modifying Employee Penalty", str(e))
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

						# ? EMAIL SHOULD ONLY SENT IN AUTO APPROVAL CASE IF IT IS ENABLE IN HR SETTINGS
						if not self.is_new():
							auto_approve = frappe.db.get_value("Attendance Regularization", self.name, "auto_approve")
							if auto_approve:
								is_email_sent_allowed = frappe.db.get_single_value("HR Settings", "custom_send_auto_approve_doc_emails") or 0
								if not is_email_sent_allowed:
									return
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

					# ? EMAIL SHOULD ONLY SENT IN AUTO APPROVAL CASE IF IT IS ENABLE IN HR SETTINGS
					if not self.is_new():
						auto_approve = frappe.db.get_value("Attendance Regularization", self.name, "auto_approve")
						if auto_approve:
							is_email_sent_allowed = frappe.db.get_single_value("HR Settings", "custom_send_auto_approve_doc_emails") or 0
							if not is_email_sent_allowed:
								return

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
		if (self.regularization_date and self.employee):
			attendance_id = frappe.db.get_value(
				"Attendance",
				{
					"attendance_date": self.regularization_date,
					"employee": self.employee,
					"docstatus": ["!=", 2]   # exclude cancelled records
				},
				"name"
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

	def before_validate(self):
		if not self.is_new():
			if self.workflow_state == "Rejected":
				self.status = "Rejected"
			elif self.workflow_state == "Approved":
				self.status = "Approved"


	def on_update(self):
		if self.workflow_state == "Pending":
			manager_info = get_reporting_manager_info(self.employee)
			if manager_info:
				#! STORE AS: <manager_docname> - <manager_employee_name>
				self.db_set("pending_approval_at", f"{manager_info['name']} - {manager_info['employee_name']}")

		else:
			self.db_set("pending_approval_at", "")

def validate_in_out_time(doc):
    """
    VALIDATE THAT EACH ROW IN THE CHECK-IN / PUNCH DETAILS TABLE
    HAS AN 'IN TIME' THAT IS STRICTLY EARLIER THAN ITS 'OUT TIME'.
    RAISES A VALIDATION ERROR IF THE CONDITION IS NOT MET.
    """
    #! ENSURE THERE ARE CHECK-IN / PUNCH DETAIL RECORDS
    if not doc.checkinpunch_details:
        return

    #? LOOP THROUGH EACH PUNCH DETAIL ROW
    for row in doc.checkinpunch_details:
        #? PROCEED ONLY IF BOTH TIMES ARE ENTERED
        if row.in_time and row.out_time:
            #? VALIDATE THAT IN-TIME IS STRICTLY BEFORE OUT-TIME
            if row.in_time >= row.out_time:
                frappe.throw(
                    _(
                        "Row {0}: The check-in time ({1}) must be earlier than the check-out time ({2})."
                    ).format(row.idx, row.in_time, row.out_time)
                )
