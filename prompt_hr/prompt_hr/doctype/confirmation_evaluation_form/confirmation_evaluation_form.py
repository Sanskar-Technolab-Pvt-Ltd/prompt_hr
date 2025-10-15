# Copyright (c) 2025, Jignasha Chavda and contributors
# For license information, please see license.txt

import frappe
from frappe.utils import today, add_days, add_to_date, getdate
from frappe.model.document import Document
from prompt_hr.utils import get_next_date, convert_month_to_days
from prompt_hr.py.utils import send_notification_email, check_user_is_reporting_manager

class ConfirmationEvaluationForm(Document):
	
	def before_save(self):
		
		try:
			# * IF COMPANY IS PROMPT
									
			#* CHECKING IF THE REPORTING HEAD OR DEPARTMENT OF HEAD HAS ENTERED THE RATING 
				user = frappe.session.user
				form_url = frappe.utils.get_url_to_form(self.doctype, self.name)

				reporting_manager = self.reporting_manager or frappe.db.get_value("Employee", self.employee, "reports_to") or None

				user_employee = frappe.db.get_value("Employee", {"user_id": user}, "name") or None

				is_reporting_head = True if (reporting_manager and user_employee) and user_employee == reporting_manager else False

				is_head_of_department = True if (self.hod and user_employee) and user_employee == self.hod else False

				if (is_reporting_head or is_head_of_department) and (self.table_txep and len(self.table_txep) > 0):
					
					if is_reporting_head:
						if any(row.rh_rating in ["", None, 0.0, 0] for row in self.table_txep):            
							frappe.throw("Please provide appropriate ratings")
						else:
							hr_user_list = frappe.db.get_all("Has Role", filters={"role": ["in", ["S - HR Director (Global Admin)", "S - HR L1"]], "parenttype": "User", "parent": ["not in", [user, "Administrator"]]}, fields=["parent"], pluck="parent")
							
							hod_user = frappe.db.get_value("Employee", self.hod, "user_id")

							subject = f"Confirmation Evaluation Form - {self.employee}"
							if hod_user:
								message = f"<p>The reporting manager, {self.reporting_manager}, has submitted ratings for the Confirmation Evaluation Form of {self.employee}. We now request you to provide your ratings</p><p>You can access the form using the link below:Confirmation Evaluation Form Link:{form_url}</p>"

								send_notification_email(recipients=[hod_user], doctype=self.doctype, docname=self.name, notification_name=0,fallback_message=message, fallback_subject=subject, send_header_greeting=True, send_link=False)

							if hr_user_list:
								message = f"<p>The reporting manager, {self.reporting_manager}, has submitted ratings for the Confirmation Evaluation Form of {self.employee}. The process is now with the HOD, {self.hod}.</p><p>You can access the form through the link below: </p><p>Confirmation Evaluation Form Link: {form_url}</p>"

								send_notification_email(recipients=hr_user_list, doctype=self.doctype, docname=self.name, notification_name=0,fallback_message=message, fallback_subject=subject, send_header_greeting=True, send_link=False)
						
					elif is_head_of_department:
						if any(row.dh_rating in ["", None, 0.0, 0] for row in self.table_txep):
							frappe.throw("Please provide appropriate ratings")
						else:
							
							hr_user_list = frappe.db.get_all("Has Role", filters={"role": ["in", ["S - HR Director (Global Admin)", "S - HR L1"]], "parenttype": "User", "parent": ["not in", [user, "Administrator"]]}, fields=["parent"], pluck="parent")

							if hr_user_list:
								subject = f"Confirmation Evaluation Form - {self.employee}"

								message = f"<p>The Department Head, {self.hod}, has submitted ratings for the Confirmation Evaluation Form of {self.employee}. Please take further actions</p><p>You can access the form through the link below: </p><p>Confirmation Evaluation Form Link: {form_url}</p>"

								send_notification_email(recipients=hr_user_list, doctype=self.doctype, docname=self.name, notification_name=0,fallback_message=message, fallback_subject=subject, send_header_greeting=True, send_link=False)															
		except Exception as e:
			frappe.log_error(frappe.get_traceback(), "Error in Confirmation Evaluation Form")
			# frappe.throw(f"{str(e)}")
	

	def after_insert(self):
		
		if self.reporting_manager:
			rh_user = frappe.db.get_value("Employee", self.reporting_manager, "user_id")
		else:
			rh_user = None
		
		hr_roles = ["S - HR Director (Global Admin)", "S - HR L1"]

		if rh_user:
			hr_user_list = frappe.db.get_all("Has Role", {"parenttype":"User", "parent": ["not in", [rh_user, "Administrator"]], "role": ["in", hr_roles]}, "parent", pluck="parent")
		else:
			hr_user_list = frappe.db.get_all("Has Role", {"parenttype":"User", "role": ["in", hr_roles], "parent": ["not in", ["Administrator"]]}, "parent", pluck="parent")

		try:
			
			subject = f"Confirmation Feedback Form-{self.employee}"
			form_url = frappe.utils.get_url_to_form(self.doctype, self.name)


			frappe.log_error("confirmation_after_insert_mail_send", f"hr user list {hr_user_list}")
			if hr_user_list:
				message = f"<p>Confirmation Feedback Form has been generated for employee {self.employee}.</p><p>You can access the form using the following link:</p><p>Confirmation Feedback Form Link:{form_url}</p>"

				send_notification_email(recipients=hr_user_list, doctype=self.doctype, docname=self.name, notification_name=0,fallback_message=message, fallback_subject=subject, send_header_greeting=True, send_link=False)

			if rh_user:
				message = f"<p>Confirmation Feedback Form has been generated for employee {self.employee}. Kindly review the form and provide your ratings.</p><p>You can access the form using the following link:</p><p>Confirmation Feedback Form Link:{form_url}</p>"

				send_notification_email(recipients=[rh_user], doctype=self.doctype, docname=self.name, notification_name=0,fallback_message=message, fallback_subject=subject, send_header_greeting=True, send_link=False)
    
		except Exception as e:
			frappe.log_error("error_while_sending_confirmation_form_creation_mails", frappe.get_traceback())

	def on_update(self):
		
		if self.workflow_state == "Pending":
			self.db_set("pending_approval_at", self.reporting_manager)
		elif self.workflow_state == "Submitted by RM":
			self.db_set("pending_approval_at", self.hod)
		elif self.workflow_state == "Submitted by DH" and self.pending_approval_at:
			self.db_set("pending_approval_at", "")
		

	@frappe.whitelist()
	def is_probation_feedback_rating_added(self):
		user =  frappe.session.user
		reporting_manager = self.reporting_manager or (frappe.db.get_value("Employee", self.employee, "reports_to") or None)
		hod = self.hod or None
		is_reporting_head = False


		if reporting_manager:
			is_reporting_head = True if user == frappe.db.get_value("Employee", reporting_manager, "user_id") else False
			if is_reporting_head:
				first_probation_feedback = frappe.db.get_value("Employee", self.employee, "custom_first_probation_feedback")
				second_probation_feedback = frappe.db.get_value("Employee", self.employee, "custom_second_probation_feedback")

				if first_probation_feedback and second_probation_feedback:
					ratings_added_in_first_form = 1 if frappe.db.get_value("Probation Feedback Form", first_probation_feedback, "docstatus") else 0
					ratings_added_in_second_form = 1 if frappe.db.get_value("Probation Feedback Form", second_probation_feedback, "docstatus") else 0
    
					if not ratings_added_in_first_form and not ratings_added_in_second_form:
						frappe.throw("Please add ratings in 30 Days and 60 Days probation feedback form and <b>Submit</b> before submitting this form.")
					elif not ratings_added_in_first_form:
						frappe.throw("Please add ratings in 30 Days probation feedback form and <b>Submit</b> before submitting this form.")
					elif not ratings_added_in_second_form:
						frappe.throw("Please add ratings in 60 Days probation feedback form and <b>Submit</b> before submitting this form.")