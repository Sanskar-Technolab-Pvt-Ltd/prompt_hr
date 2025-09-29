# Copyright (c) 2025, Jignasha Chavda and contributors
# For license information, please see license.txt

import frappe
from frappe import _, throw
from frappe.utils import getdate, today, formatdate
from frappe.model.document import Document
from prompt_hr.py.utils import send_notification_email, is_user_reporting_manager_or_hr, get_reporting_manager_info
from prompt_hr.overrides.attendance_override import modify_employee_penalty
from prompt_hr.prompt_hr.doctype.employee_penalty.employee_penalty import cancel_penalties
from prompt_hr.py.auto_mark_attendance import mark_attendance


class WeekOffChangeRequest(Document):

	def on_update(self):
		if self.workflow_state == "Pending":
			manager_info = get_reporting_manager_info(self.employee)
			if manager_info:
				self.db_set("pending_approval_at", f"{manager_info['name']} - {manager_info['employee_name']}")
		else:
			self.db_set("pending_approval_at", "")
	
	def before_insert(self):
    
		# * CHECKING IF THE DAY IS ENTERED OR NOT AND IF ENTERED THEN THE DAY IS CORRECT OR NOT ACCORDING TO DATE
		if self.weekoff_details:
			for row in  self.weekoff_details:
				if row.existing_weekoff_date:
					day_name = get_day_name(row.existing_weekoff_date)
					if not row.existing_weekoff:
						row.existing_weekoff = day_name
					elif row.existing_weekoff and row.existing_weekoff.lower() != day_name.lower():
						throw("Please Set Correct Existing weekoff Day as per the date")

				if row.new_weekoff_date:
					day_name = get_day_name(row.new_weekoff_date)
					if not row.new_weekoff:
						row.new_weekoff = day_name
					elif row.new_weekoff and row.new_weekoff.lower() != day_name.lower():
						throw("Please Set Correct New weekoff Day as per the date")
	def validate(self):

		# *CHECKING IF THE EXISTING DETAILS IS VALID OR NOT, IF INVALID SHOWING AN ALERT TELLING USER THAT THE EXISTING DATE ENTERED DOES NOT EXISTS IN HOLIDAY LIST
		if self.weekoff_details:
			for row in  self.weekoff_details:
				exists = check_existing_date(self.employee, row.existing_weekoff_date)
				if not exists.get("error"):
					if not exists.get("exists"):
						throw(f"Date {row.existing_weekoff_date} does not exist in holiday list")
					else:
						if row.existing_weekoff_date:
							day_name = get_day_name(row.existing_weekoff_date)
							if not row.existing_weekoff:
								row.existing_weekoff = day_name
							elif row.existing_weekoff and row.existing_weekoff.lower() != day_name.lower():
								throw(f"The date {formatdate(row.existing_weekoff_date, 'dd-mm-yyyy')} does not exist in the holiday list for this employee.")

						if row.new_weekoff_date:
							day_name = get_day_name(row.new_weekoff_date)
							if not row.new_weekoff:
								row.new_weekoff = day_name
							elif row.new_weekoff and row.new_weekoff.lower() != day_name.lower():
								throw("Please Set Correct New weekoff Day as per the date")
				elif exists.get("error"):
					throw(f"Error While Verifying Existing Date {exists.get('message')}")


		# *CHECKING IF THE CURRENT USER IS THE EMPLOYEE USER LINKED TO DOCUMENT THEN WHEN WE SAVES THIS DOCUMENT THEN SENDING AN EMAIL TO THE EMPLOYEE'S REPORTING HEAD ABOUT THE CREATION WEEKOFF CHANGE REQUEST
		current_user = frappe.session.user
		if self.status == "Approved":
			is_rh = is_user_reporting_manager_or_hr(current_user, self.employee)
			#! PROCESS WEEKOFF CHANGES FOR EMPLOYEE
			if not is_rh.get("error"):
				today = getdate()

				def process_weekoff_attendance(date, is_existing):
					att_list = frappe.get_all(
						"Attendance",
						filters={
							"employee": self.employee,
							"docstatus": ["!=", 2],
							"attendance_date": date
						},
						fields=["name", "attendance_date", "custom_employee_penalty_id"],
						limit=1
					)

					if att_list:
						attendance = att_list[0]

						# Cancel penalties if any
						if attendance.custom_employee_penalty_id:
							cancel_penalties(
								attendance.custom_employee_penalty_id,
								"Weekoff change request Approve",
								1
							)

						# Cancel old attendance
						frappe.get_doc("Attendance", attendance.name).cancel()
					print("ATtendance")
					# Mark attendance
					mark_attendance(
						attendance_date=date,
						company=self.company,
						regularize_attendance=0,
						emp_id=self.employee
					)

					# Update employee penalty
					modify_employee_penalty(self.employee, date, is_existing)

				for weekoff_detail in self.weekoff_details:
					existing_date = getdate(weekoff_detail.existing_weekoff_date)
					if existing_date < today:
						process_weekoff_attendance(weekoff_detail.existing_weekoff_date, True)

					new_date = getdate(weekoff_detail.new_weekoff_date)
					if new_date < today:
						process_weekoff_attendance(weekoff_detail.new_weekoff_date, False)


			if not is_rh.get("error") and is_rh.get("is_rh"):
				emp_user_id = frappe.db.get_value("Employee", self.employee, "user_id")
				if emp_user_id:
					# if "@" in emp_user_id:
					# 	emp_mail = emp_user_id
					# else:
					# emp_mail = frappe.db.get_value("User", emp_user_id, 'email')
					send_notification_email(
							recipients=[emp_user_id],
							notification_name="WeekOff Change Request Approved",
							doctype="WeekOff Change Request",
							docname=self.name,
							send_link=True,
							fallback_subject='WeekOff Change Request Approved',
							fallback_message=f"<p>Dear Employee</p>   <p>Your WeekOff Change Request has been reviewed and approved.<br>Best regards,<br>HR Department</p>"
						)
			elif is_rh.get("error"):
				throw(f"{is_rh.get('message')}")
		if self.status == "Rejected":
			is_rh = is_user_reporting_manager_or_hr(current_user, self.employee)
			if not is_rh.get("error") and is_rh.get("is_rh"):
				emp_user_id = frappe.db.get_value("Employee", self.employee, "user_id")
				if emp_user_id:
					send_notification_email(
							recipients=[emp_user_id],
							notification_name="WeekOff Change Request Rejected",
							doctype="WeekOff Change Request",
							docname=self.name,
							send_link=True,
							fallback_subject='WeekOff Change Request Rejected',
							fallback_message=f"<p>Dear Employee</p>\n\n    <p>We regret to inform you that your WeekOff Change Request has been rejected.</p>"
						)
			elif is_rh.get("error"):
				throw(f"{is_rh.get('message')}")
    
	def after_insert(self):
		
		current_user = frappe.session.user
		emp_user = frappe.db.get_value("Employee", self.employee, "user_id")

		# * NOTIFY REPORTING MANAGER IF THE CURRENT USER IS THE EMPLOYEE WHOSE WEEKOFF CHANGE REQUEST IS RAISED FOR
		notify_reporting_manager(self.employee, self.name, emp_user, current_user)

	def before_validate(self):
		if not self.is_new():
			if self.workflow_state == "Rejected":
				self.status = "Rejected"
			elif self.workflow_state == "Approved":
				self.status = "Approved"

def notify_reporting_manager(employee_id, docname, emp_user, current_user):
	"""Method to check if the current user is the employee whose weekoff change request is, if it is the same user then, sending an email to  employee's reporting manager
	"""
	rh_emp = frappe.db.get_value("Employee", employee_id, "reports_to")
	if rh_emp:
		rh_user = frappe.db.get_value("Employee", rh_emp, "user_id")
		if rh_user:
			if current_user == emp_user:
				send_notification_email(
					recipients=[rh_user],
					notification_name="Request to RH to Approve WeekOff Change",
					doctype="WeekOff Change Request",
					docname= docname,
					send_link=True,
					fallback_subject=" Request for Approval – WeekOff Change Request",
					fallback_message=f"Dear Reporting Head,\n\n     I am writing to formally request your approval for my WeekOff Change Request.\n Kindly review and approve the request at your earliest convenience."
				)
		else:
			throw(f"No user found for reporting head {rh_emp}")
	else:
		throw(f"NO Reporting Head Found for Employee {employee_id}")

@frappe.whitelist()
def check_existing_date(employee_id, existing_date):
	"""Method to check of the existing date entered exists in holiday list's holiday child table or not"""
	try:
		holiday_list_id = frappe.db.get_value("Employee", employee_id, "holiday_list") or None
		
		if holiday_list_id:
			is_existing = frappe.db.get_all("Holiday", {"parenttype": "Holiday List", "parent": holiday_list_id, "holiday_date": existing_date}, "name", limit=1)
		
			if is_existing:
				return {"error": 0,"exists": 1}
			else:
				return {"error": 0, "exists": 0}
		else:
			return {"error": 1, "message": f"No Holiday List found for {employee_id}"}
	except Exception as e:
		frappe.log_error("Error While Verifying Existing Date", frappe.get_traceback())
		return {"error": 1, "message": f"{str(e)}"}



def get_day_name(date_value):
	try:
		date_value = getdate(date_value)
		day_name = date_value.strftime('%A')
		return day_name
	except Exception as e:
		throw("Error while Getting Date Day name")
