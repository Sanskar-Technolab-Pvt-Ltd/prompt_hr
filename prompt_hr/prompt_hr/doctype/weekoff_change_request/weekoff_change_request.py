# Copyright (c) 2025, Jignasha Chavda and contributors
# For license information, please see license.txt

import frappe
from frappe import _, throw
from frappe.utils import getdate, today
from frappe.model.document import Document
from prompt_hr.py.utils import send_notification_email


class WeekOffChangeRequest(Document):
	
	def validate(self):

		# *CHECKING IF THE EXISTING DETAILS IS VALID OR NOT, IF INVALID SHOWING AN ALERT TELLING USER THAT THE EXISTING DATE ENTERED DOES NOT EXISTS IN HOLIDAY LIST
		if self.weekoff_details:
			for row in  self.weekoff_details:
				exists = check_existing_date(self.employee, row.existing_weekoff_date)
				if not exists.get("error"):
					if not exists.get("exists"):
						throw(f"Date {row.existing_weekoff_date} does not exist in holiday list")
				elif exists.get("error"):
					throw(f"Error While Verifying Existing Date {exists.get('message')}")
					
	
@frappe.whitelist()
def check_existing_date(employee_id, existing_date):
	"""Method to check of the existing date entered exists in holiday list's holiday child table or not"""
	try:
		holiday_list_id = frappe.db.get_value("Employee", employee_id, "holiday_list")
		
		is_existing = frappe.db.get_all("Holiday", {"parenttype": "Holiday List", "parent": holiday_list_id, "holiday_date": existing_date}, "description")
		
		if is_existing:
			return {"error": 0,"exists": 1, "day": is_existing[0].get("description")}
		else:
			return {"error": 0, "exists": 0}
	except Exception as e:
		frappe.log_error("Error While Verifying Existing Date", frappe.get_traceback())
		return {"error": 1, "message": f"{str(e)}"}




@frappe.whitelist()
def check_user_is_reporting_manager(user_id, requesting_employee_id):
	""" Method to check if the current user is Employees reporting manager
	"""
	try:
		reporting_manager_emp_id = frappe.db.get_value("Employee", requesting_employee_id, "reports_to")

		if reporting_manager_emp_id:
			rh_user_id = frappe.db.get_value("Employee", reporting_manager_emp_id, "user_id")
			if rh_user_id and (user_id == rh_user_id):
				return {"error": 0, "is_rh": 1}
			else:
				return {"error": 0, "is_rh": 0}
		else:
			return {"error": 0, "is_rh": 0}
	except Exception as e:
		frappe.log_error("Error while Verifying User", frappe.get_traceback())
		return {"error":1, "message": f"{str(e)}"}
# @frappe.whitelist()
# def check_user_is_reporting_manager(user_id, requesting_employee_id):
    
# 	reporting_head_id = frappe.db.get_value("Employee", requesting_employee_id, "reports_to")
    
# 	if reporting_head_id:
# 		reporting_head_user_id = frappe.db.get_value("Employee", reporting_head_id, "user_id")
# 		if reporting_head_user_id:
# 			reporting_manager_email = frappe.db.get_user("User", reporting_head_user_id, "email")
# 			if reporting_manager_email:
# 					send_notification_email(
# 						recipients=[reporting_manager_email],
# 						notification_name="Request to RH to Approve WeekOff Change",
# 						doctype="WeekOff Change Request",

# 					)
# 			else:
# 				return {"error": 1, "message": f"No Reporting Manager Email found for employee {reporting_head_user_id}"}
# 		else:
# 			return {"error": 1, "message": f"No Reporting Manager User ID found for employee {reporting_head_user_id}"}

# 	else:
# 		return {"error": 1, "message": f"No Reporting Manager found for employee {requesting_employee_id}"}

    

@frappe.whitelist()
def send_mail_to_reporting_head():
    pass