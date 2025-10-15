# Copyright (c) 2025, Jignasha Chavda and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document
from prompt_hr.utils import get_next_date, convert_month_to_days
from prompt_hr.py.utils import send_notification_email
class ProbationFeedbackForm(Document):
	
	def after_insert(self):
		probation_for = None
		if self.probation_feedback_for == "30 Days":
			probation_for = "First"
		elif self.probation_feedback_for == "60 Days":
			probation_for = "Second"
			
		# *GETTING REPORTING HEAD USER OF THE EMPLOYEE
		if self.reporting_manager:
			rh_user = frappe.db.get_value("Employee", self.reporting_manager, "user_id") or  None
		else:
			rh_user = None
			frappe.log_error("error_while_sending_feedback_creation_mail_to_hr", "No rh emp")


		# *GETTING USER WITH HR ROLES AND THEN SENDING MAIL TO EMPLOYEES LINKED TO THESE USERS
		hr_roles = ["S - HR Director (Global Admin)", "S - HR L1"]
		if rh_user:
			users_with_hr_roles = frappe.db.get_all("Has Role", {"parenttype": "User", "parent": ["not in", [rh_user, "Administrator"]],"role": ["in", hr_roles]}, "parent", pluck="parent")
		else:
			users_with_hr_roles = frappe.db.get_all("Has Role", {"parenttype": "User","role": ["in", hr_roles], "parent": ["not in", [rh_user, "Administrator"]]}, "parent", pluck="parent")
	
		try:			
			form_url = frappe.utils.get_url_to_form(self.doctype, self.name)
			subject = f"{probation_for}" if probation_for else ""
			subject += f" Probation Feedback Form - {self.employee}"

			if users_with_hr_roles:					
				message = f"<p>{probation_for}" if probation_for else "<p>"
				message += f""" Probation Feedback Form has been generated for employee {self.employee}.You can access the form using the following link: </p> <br><p>{probation_for if probation_for else ""} Probation Feedback Form Link: {form_url}</p>
				"""
				send_notification_email(recipients=users_with_hr_roles,doctype=self.doctype, docname=self.name, notification_name=0,fallback_message=message, fallback_subject=subject, send_header_greeting=True, send_link=False)
			else:
				frappe.log_error("error_while_sending_feedback_creation_mail_to_hr", "NO user with hr roles")

			if rh_user:
				message = f"<p>{probation_for}" if probation_for else "<p>"
				message += f""" Probation Feedback Form has been generated for employee {self.employee}. Kindly review the form and provide your ratings,</p><br><p>You can access the form using the following link: {form_url}"""

				send_notification_email(recipients=[rh_user],doctype=self.doctype, docname=self.name, notification_name=0,fallback_message=message, fallback_subject=subject, send_header_greeting=True, send_link=False)
				
		except Exception as e:
			frappe.log_error("error_while_sending_feedback_creation_mail_to_hr", frappe.get_traceback())
				
	

	def before_save(self):

			probation_for = None
			if self.probation_feedback_for == "30 Days":
				probation_for = "First"
			elif self.probation_feedback_for == "60 Days":
				probation_for = "Second"
    
			user = frappe.session.user
			form_url = frappe.utils.get_url_to_form(self.doctype, self.name)

			reporting_manager = self.reporting_manager or frappe.db.get_value("Employee", self.employee, "reports_to") or None

			user_employee = frappe.db.get_value("Employee", {"user_id": user}, "name") or None

			is_reporting_head = True if (reporting_manager and user_employee) and user_employee == reporting_manager else False

			is_head_of_department = True if (self.hod and user_employee) and user_employee == self.hod else False

			print(f"\n\n DETAILS {user}  {reporting_manager} {user_employee} {is_reporting_head}  {is_head_of_department}\n\n")

			if (is_reporting_head or is_head_of_department):
				
				if is_reporting_head:
					if any(row.rating in ["", None, 0.0, 0] for row in self.probation_feedback_prompt):            
						frappe.throw("Please provide appropriate ratings")
					else:						    
						hr_user_list = frappe.db.get_all("Has Role", filters={"role": ["in", ["S - HR Director (Global Admin)", "S - HR L1"]], "parenttype": "User", "parent": ["not in", [user, "Administrator"]]}, fields=["parent"], pluck="parent")

						subject = f"{probation_for} Probation Feedback Form - {self.employee}"
    
						if hr_user_list:
							message = f"<p>The reporting manager, {self.reporting_manager}, has submitted ratings for the {probation_for} Probation Feedback Form of {self.employee}. The process is now with the HOD, {self.hod}.</p><p>You can access the form through the link below: {probation_for} Probation Feedback Form Link: {form_url}</p>"
							try:
								send_notification_email(recipients=hr_user_list, doctype=self.doctype, docname=self.name, notification_name=0,fallback_message=message, fallback_subject=subject, send_header_greeting=True, send_link=False)
    
							except Exception as e:
								frappe.log_error("error_while_sending_mail", frappe.get_traceback())
	
	def on_update(self):
		print(f"\n\n ON UPDATE CALLED \n\n")
		if self.docstatus == 0:
			self.db_set("pending_approval_at", self.reporting_manager)
		elif self.docstatus == 1:
			self.db_set("pending_approval_at", "")

#* THIS METHOD IS CALLED UNDER frappe.call IN probation_feedback_form.js
# !NOT IN USE. USED IN probation_feedback_form.js BUT THERE CODE IS COMMENTED
@frappe.whitelist(allow_guest=True)
def send_mail_to_hr(docname):
	"""Method to send mail to HR When Dotted Manager Confirm's his Ratings
		"""
	try:
		
		all_hr_role_user = frappe.get_all("Has Role", filters={"role": "S - HR Director (Global Admin)", "parenttype": "User"}, fields=["parent"])
		company_abbr = frappe.db.get_single_value("HR Settings", "custom_indifoss_abbr")
		if company_abbr:
			company_id = frappe.db.get_value("Company", {"abbr": company_abbr}, "name")
			if company_id and all_hr_role_user:
				for hr_user in all_hr_role_user:
					if frappe.db.exists("Employee", {"user_id": hr_user.get("parent"), "status": "Active", "company": company_id}):
						if hr_user.get("parent"):
								send_notification_email(
									recipients=[hr_user.get("parent")],
									notification_name = "Dotted Manager to HR For Probation Feedback Form",
									doctype = "Probation Feedback Form",
									docname = docname,
									fallback_subject = "Probation Feedback Ratings Added by Dotted Manager",
									fallback_message = f"Hi HR, \n\n     The dotted manager has added their ratings and remarks in the Probation Feedback Form.\n The form is now complete and ready for your review."
								)
								return {"error": 0}
						else:
							return {"error": 1, "message": "No HR Email Found"}
			else:
				return {"error": 1, "message": "No HR users found."}
		else:
			return {"error": 1, "message": "No Company abbr found for the IndiFOSS Company from HR Settings"}
	except Exception as e:
		frappe.log_error(f"Error updating job applicant status", frappe.get_traceback())
		return {"error": 1, "message": f"Error Sending mail to HR {str(e)} \n For More Info Check Error Log"}
    
    

#* THIS METHOD IS CALLED UNDER frappe.call IN probation_feedback_form.js
# !NOT IN USE. USED IN probation_feedback_form.js BUT THERE CODE IS COMMENTED

@frappe.whitelist()
def get_feedback_days_for_indifoss():
	"""Method to get the Feedback and confirmation days from HR Settings of IndiFOSS Company
	"""
	try:
		settings = frappe.get_single("HR Settings")
		return {
			"error": 0,
			"first_feedback_days": settings.custom_first_feedback_after_for_indifoss or  45,
			"second_feedback_days": settings.custom_second_feedback_after_for_indifoss or 90,
			"confirmation_days": settings.custom_release_confirmation_form_for_indifoss or 180
		}
	except Exception as e:
		frappe.log_error("Error While fetching IndiFOSS feedback and confirmation days", frappe.get_traceback())
		return {"error": 1, "message": f"{str(e)}"}