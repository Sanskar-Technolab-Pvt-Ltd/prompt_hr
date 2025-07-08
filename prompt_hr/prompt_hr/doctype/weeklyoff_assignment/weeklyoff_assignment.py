# Copyright (c) 2025, Jignasha Chavda and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document
from prompt_hr.py.utils import send_notification_email
from frappe.utils import getdate
from hrms.hr.utils import get_holiday_list_for_employee
from frappe.utils import getdate
from datetime import date
from datetime import timedelta
import calendar
from dateutil import relativedelta
from datetime import date

class WeeklyOffAssignment(Document):

	def before_submit(self):

		# ! END DATE MUST BE GREATER THAN START DATE
		if getdate(self.end_date) <= getdate(self.start_date):
			frappe.throw("End Date must be greater than or equal to Start Date.")

		# ! VALIDATE PRESENCE of OLD and NEW WEEKLY OFF TYPES
		if not self.old_weeklyoff_type and not self.new_weeklyoff_type:
			frappe.throw("Both Old Weekly Off Type and New Weekly Off Type must be specified before submission.")
		elif not self.old_weeklyoff_type:
			frappe.throw("Please specify the Old Weekly Off Type before submission.")
		elif not self.new_weeklyoff_type:
			frappe.throw("Please specify the New Weekly Off Type before submission.")


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

		# * Step 1: Determine current year range based on assignment start date
		year = getdate(self.start_date).year
		year_start = date(year, 1, 1)
		year_end = date(year, 12, 31)


		# * Step 2: Check if holiday list already exists
		is_holiday_list_exist = frappe.db.exists("Holiday List", f"{self.employee} - Holiday List - {year}")

		# * Step 3: Create new Holiday List if none exists and no prior record
		if not is_holiday_list_exist:
			holiday_list = get_holiday_list_for_employee(self.employee)
			if holiday_list:
				# ? Fetch non-optional holidays from existing list
				base_holidays = frappe.get_all(
					"Holiday",
					filters={
						"parent": holiday_list,
						"custom_is_optional_festival_leave": 0,
						"holiday_date": ["between", [year_start, year_end]],
						"weekly_off": 0
					},
					fields=["holiday_date", "description"]
				)

				holiday_dates = {(h.holiday_date,h.description) for h in base_holidays}
				final_holidays = [{"holiday_date": h[0], "weekly_off": 0, "description":h[1]} for h in sorted(holiday_dates)]

				# ! Add new weekly offs during assignment
				new_week_days = frappe.get_all(
					"WeekOff Multiselect",
					filters={"parenttype": "WeeklyOff Type", "parent": self.new_weeklyoff_type},
					pluck="weekoff"
				)

				for week_day in new_week_days:
					weekday_index = getattr(calendar, week_day.upper())
					ref_date = getdate(self.start_date) + relativedelta.relativedelta(weekday=weekday_index)
					while ref_date <= getdate(self.end_date):
						final_holidays.append({
							"holiday_date": ref_date,
							"description": week_day,
							"weekly_off": 1
						})
						ref_date += timedelta(days=7)

				# ! Add old weekly offs before and after assignment
				old_week_days = frappe.get_all(
					"WeekOff Multiselect",
					filters={"parenttype": "WeeklyOff Type", "parent": self.old_weeklyoff_type},
					pluck="weekoff"
				)

				# Before assignment
				for week_day in old_week_days:
					weekday_index = getattr(calendar, week_day.upper())
					ref_date = getdate(year_start) + relativedelta.relativedelta(weekday=weekday_index)
					while ref_date < getdate(self.start_date):
						final_holidays.append({
							"holiday_date": ref_date,
							"description": week_day,
							"weekly_off": 1
						})
						ref_date += timedelta(days=7)

				# After assignment
				for week_day in old_week_days:
					weekday_index = getattr(calendar, week_day.upper())
					ref_date = getdate(self.end_date) + timedelta(days=1)
					ref_date += relativedelta.relativedelta(weekday=weekday_index)
					while ref_date <= getdate(year_end):
						final_holidays.append({
							"holiday_date": ref_date,
							"description": week_day,
							"weekly_off": 1
						})
						ref_date += timedelta(days=7)

				# * Create and insert new Holiday List doc
				holiday_doc = frappe.get_doc({
					"doctype": "Holiday List",
					"holiday_list_name": f"{self.employee} - Holiday List - {year}",
					"name": f"{self.employee} - Holiday List - {year}",
					"from_date": getdate(year_start),
					"to_date": getdate(year_end),
					"holidays": final_holidays
				})
				holiday_doc.insert(ignore_permissions=True)

				# * Assign holiday list to employee
				frappe.get_doc("Employee", self.employee).db_set("holiday_list", holiday_doc.name)

		# * Step 4: Update existing Holiday List for assignment range
		else:
			holiday_list = get_holiday_list_for_employee(self.employee)
			if holiday_list and is_holiday_list_exist:
				holiday_doc = frappe.get_doc("Holiday List", f"{self.employee} - Holiday List - {year}")

				# ! Remove weekly offs in the assignment range
				holiday_doc.holidays = [
					h for h in holiday_doc.holidays
					if not (getdate(self.start_date) <= getdate(h.holiday_date) <= getdate(self.end_date) and h.weekly_off)
				]

				# ! Add new weekly offs
				new_week_days = frappe.get_all(
					"WeekOff Multiselect",
					filters={"parenttype": "WeeklyOff Type", "parent": self.new_weeklyoff_type},
					pluck="weekoff"
				)

				for week_day in new_week_days:
					weekday_index = getattr(calendar, week_day.upper())
					ref_date = getdate(self.start_date) + relativedelta.relativedelta(weekday=weekday_index)
					while ref_date <= getdate(self.end_date):
						holiday_doc.append("holidays", {
							"holiday_date": ref_date,
							"description": week_day,
							"weekly_off": 1
						})
						ref_date += timedelta(days=7)

				# * Save the updated holiday list
				holiday_doc.save(ignore_permissions=True)
				# * Reassign holiday list to employee (optional but safe)
				frappe.get_doc("Employee", self.employee).db_set("holiday_list", holiday_doc.name)

	def on_cancel(self):
		year = getdate(self.start_date).year
		is_holiday_list_exist = frappe.db.exists("Holiday List", f"{self.employee} - Holiday List - {year}")
		if is_holiday_list_exist:
			holiday_doc = frappe.get_doc("Holiday List", f"{self.employee} - Holiday List - {year}")
			# ! Remove weekly offs in the assignment range
			holiday_doc.holidays = [
				h for h in holiday_doc.holidays
				if not (getdate(self.start_date) <= getdate(h.holiday_date) <= getdate(self.end_date) and h.weekly_off)
			]

			# ! Add Old weekly offs Again on Cancel
			new_week_days = frappe.get_all(
				"WeekOff Multiselect",
				filters={"parenttype": "WeeklyOff Type", "parent": self.old_weeklyoff_type},
				pluck="weekoff"
			)

			for week_day in new_week_days:
				weekday_index = getattr(calendar, week_day.upper())
				ref_date = getdate(self.start_date) + relativedelta.relativedelta(weekday=weekday_index)
				while ref_date <= getdate(self.end_date):
					holiday_doc.append("holidays", {
						"holiday_date": ref_date,
						"description": week_day,
						"weekly_off": 1
					})
					ref_date += timedelta(days=7)

			# * Save the updated holiday list
			holiday_doc.save(ignore_permissions=True)
