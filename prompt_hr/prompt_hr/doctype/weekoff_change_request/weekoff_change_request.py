# Copyright (c) 2025, Jignasha Chavda and contributors
# For license information, please see license.txt

import frappe
from frappe import _, throw
from frappe.utils import getdate, today, formatdate
from frappe.model.document import Document
from prompt_hr.py.utils import send_notification_email, check_user_is_reporting_manager
from frappe.utils import getdate
from hrms.hr.utils import get_holiday_list_for_employee
from frappe.utils import getdate
from datetime import date
from datetime import timedelta
import calendar
from dateutil import relativedelta
from datetime import date


class WeekOffChangeRequest(Document):
	
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
		# * NOT ALLOWED TO MODIFIED AFTER WEEKOFF CHANGE REQUEST IS APPROVE
		previous = self.get_doc_before_save()
		if previous and previous.status == "Approved":
			# Check if any field has changed (excluding status if desired)
			changed_fields = [
				df.fieldname
				for df in self.meta.fields
				if df.fieldtype not in ["Section Break", "Column Break"]
				and previous.get(df.fieldname) != self.get(df.fieldname)
			]

			if changed_fields:
				frappe.throw("This document has already been approved and cannot be modified.")

		# *CHECKING IF THE EXISTING DETAILS IS VALID OR NOT, IF INVALID SHOWING AN ALERT TELLING USER THAT THE EXISTING DATE ENTERED DOES NOT EXISTS IN HOLIDAY LIST
		if self.weekoff_details:
			for row in  self.weekoff_details:
				if not row.existing_weekoff_date and not row.new_weekoff_date:
					frappe.throw("Please enter both the existing and new weekoff dates to continue.")

				elif not row.existing_weekoff_date:
					frappe.throw("Please enter the existing weekoff date to continue.")

				elif not row.new_weekoff_date:
					frappe.throw("Please enter the new weekoff date to continue.")

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
			if not self.weekoff_details:
				frappe.throw("Weekoff details are missing. Approval cannot proceed without at least one entry.")

			is_rh = check_user_is_reporting_manager(current_user, self.employee)
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

			elif not is_rh.get("is_rh"):
				frappe.throw("You are not permitted to update the status. Please contact the Reporting Manager.")

		if self.status == "Rejected":
			is_rh = check_user_is_reporting_manager(current_user, self.employee)
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


	def on_update(self):
		if self.has_value_changed("status") and self.status == "Approved":
			# * Step 1: Determine current year range
			year = getdate().year
			year_start = date(year, 1, 1)
			year_end = date(year, 12, 31)

			# * Step 2: Check if Holiday List exists
			holiday_list_name = f"{self.employee} - Holiday List - {year}"
			is_holiday_list_exist = frappe.db.exists("Holiday List", holiday_list_name)

			# * Step 3: Fetch current holiday list for employee
			holiday_list = get_holiday_list_for_employee(self.employee)

			# * Step 4: If no prior assignment, request, or holiday list — create new
			if not is_holiday_list_exist:
				final_holidays = []

				if holiday_list:
					base_holidays = frappe.get_all(
						"Holiday",
						filters={
							"parent": holiday_list,
							"custom_is_optional_festival_leave": 0,
							"holiday_date": ["between", [year_start, year_end]]
						},
						fields=["holiday_date", "description", "weekly_off"]
					)

					# * Convert to list of dicts
					final_holidays = [
						{
							"holiday_date": h.holiday_date,
							"description": h.description,
							"weekly_off": h.weekly_off
						}
						for h in base_holidays
					]

				# * Remove existing and add new from this request
				for row in self.weekoff_details:
					# Remove if already present
					final_holidays = [
						h for h in final_holidays
						if h["holiday_date"] != getdate(row.existing_weekoff_date)
					]

					# Add new if valid
					if getdate(row.new_weekoff_date) and year_start <= getdate(row.new_weekoff_date) <= year_end:
						is_optional = frappe.db.get_value(
							"Holiday",
							{"parent": holiday_list, "holiday_date": getdate(row.new_weekoff_date)},
							"custom_is_optional_festival_leave"
						)
						if not is_optional:
							final_holidays.append({
								"holiday_date": getdate(row.new_weekoff_date),
								"weekly_off": 1,
								"description": getdate(row.new_weekoff_date).strftime("%A").upper()
							})

				# * Create and insert new holiday list
				holiday_doc = frappe.get_doc({
					"doctype": "Holiday List",
					"holiday_list_name": holiday_list_name,
					"name": holiday_list_name,
					"from_date": year_start,
					"to_date": year_end,
					"holidays": final_holidays
				})
				holiday_doc.insert(ignore_permissions=True)

				# * Assign to employee
				frappe.get_doc("Employee", self.employee).db_set("holiday_list", holiday_doc.name)

			# * Step 5: Else update existing holiday list
			else:
				if holiday_list and is_holiday_list_exist:
					holiday_doc = frappe.get_doc("Holiday List", holiday_list_name)

					# * Convert to list so we can iterate safely while removing
					existing_holiday_rows = list(holiday_doc.holidays)

					for row in self.weekoff_details:
						existing_date = getdate(row.existing_weekoff_date)
						new_date = getdate(row.new_weekoff_date)

						# * Remove existing weekly off date if it exists
						for h in existing_holiday_rows:
							if getdate(h.holiday_date) == existing_date and h.weekly_off:
								holiday_doc.remove(h)

						# * Add new weekly off date
						if new_date and year_start <= new_date <= year_end:
							holiday_doc.append("holidays", {
								"holiday_date": new_date,
								"weekly_off": 1,
								"description": new_date.strftime("%A")
							})

					# * Save changes
					holiday_doc.save(ignore_permissions=True)

					# * Reassign holiday list to employee (optional but safe)
					frappe.get_doc("Employee", self.employee).db_set("holiday_list", holiday_doc.name)


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
