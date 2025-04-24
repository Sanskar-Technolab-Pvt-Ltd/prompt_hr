# Copyright (c) 2025, Jignasha Chavda and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document
from prompt_hr.utils import get_next_date, convert_month_to_days

class ProbationFeedbackForm(Document):
	def on_submit(self):
		"""Method to add Probation Details to Employee if company is equal to IndiFOSS Analytical Pvt Ltd when Probation Feedback Form is submitted.
	"""
		try:
			if self.employee and self.company == "IndiFOSS Analytical Pvt Ltd":
				if self.probation_status == "Confirm":
					if self.confirmation_date:
						frappe.db.set_value("Employee", self.employee, "final_confirmation_date", self.confirmation_date)
						frappe.db.set_value("Employee", self.employee, "custom_probation_status", "Confirmed")
						
				
				elif self.probation_status == "Extend":
					probation_end_date = str(frappe.db.get_value("Employee", self.employee, "custom_probation_end_date")) or None
					
					if probation_end_date:
						# extended_probation_end_date = add_to_date(probation_end_date, months=self.extension_period)
						next_date_response = get_next_date(probation_end_date, self.extension_period)
						
						if not next_date_response.get("error"):
							
							extended_probation_end_date = next_date_response.get("message")
							
						else:
							
							frappe.throw(f"Error getting next date: {next_date_response.get('message')}")
					else:
						frappe.throw("No probation end date found for employee.")
						extended_probation_end_date = None

					
					employee_doc = frappe.get_doc("Employee", self.employee)
					
					current_user = frappe.session.user
					
					if current_user:
						employee = frappe.db.get_value("Employee", {"user_id": current_user}, ["name", "employee_name"], as_dict=True)
					else:
						employee = None
					if employee_doc:
						employee_doc.append("custom_probation_extension_details", {
							"probation_end_date": employee_doc.custom_probation_end_date,
							"extended_date": extended_probation_end_date,
							"reason": self.reason,
							"extended_by": employee.get("name") if employee else '',
							"extended_by_emp_name": employee.get("employee_name") if employee else ''
						})
						employee_doc.custom_probation_status = "Pending"
						employee_doc.custom_extended_period = convert_month_to_days(self.extension_period) or 0
						employee_doc.save(ignore_permissions=True)
						frappe.db.commit()
				
				elif self.probation_status == "Terminate":        
						frappe.db.set_value("Employee", self.employee, "custom_probation_status", "Terminated")
						frappe.db.set_value("Employee", self.employee, "relieving_date", self.last_work_date)
						frappe.db.set_value("Employee", self.employee, "reason_for_leaving", self.reason_for_termination)
		except Exception as e:
			frappe.log_error(f"Error updating job applicant status", frappe.get_traceback())
			frappe.throw(f"Error updating job applicant status: {str(e)}")
				# frappe.db.set_value("Employee", self.employee, "relieving_date", self.last_work_date)
				# frappe.db.set_value("Employee", self.employee, "reason_for_leaving", self.reason_for_termination)
	
	def validate(self):
		try:
			user = frappe.session.user
			if self.reporting_manager:
				reporting_manager_user_id = frappe.db.get_value("Employee", self.reporting_manager, "user_id")
				if reporting_manager_user_id:
					if reporting_manager_user_id == user:
						if any(row.get("180_days") not in["", None, 0.0, 0] for row in self.probation_feedback_indifoss):
							dotted_manager_emp = frappe.db.get_value("Employee", self.employee, "custom_dotted_line_manager")
							if dotted_manager_emp:
								dotted_manager_user_id = frappe.db.get_value("Employee", dotted_manager_emp, "user_id")
								if dotted_manager_user_id:
									dotted_manager_user_email = frappe.db.get_value("User", dotted_manager_user_id, "email")
									if dotted_manager_user_email:
										notification_template = frappe.get_doc("Notification", "Inform Dotted Manager about Probation Feedback")
										if notification_template:
											subject = frappe.render_template(notification_template.subject, {"doc": self})
											message = frappe.render_template(notification_template.message, {"doc": self})
											frappe.sendmail(
												recipients=[dotted_manager_user_email],
												subject= subject if subject else "Probation Feedback Form Submitted",
												message=message if message else f"Probation Feedback Form has been submitted by {self.employee_name} ({self.employee})",
											)
										else:
											frappe.sendmail(
												recipients=[dotted_manager_user_email],
												subject="Probation Feedback Form Submitted",
												message=f"Probation Feedback Form has been submitted by {self.employee_name} ({self.employee})",
											)
					else:
						print(f"\n\n not same user \n\n")
			
			

		except Exception as e:
			frappe.log_error(f"Error updating job applicant status", frappe.get_traceback())
			frappe.throw(f"Error updating job applicant status: {str(e)}")
	
	def dotted_manager_ratings(self):
		try:
			user = frappe.session.user
			dotted_manager_emp = frappe.db.get_value("Employee", self.employee, "custom_dotted_line_manager")
			if dotted_manager_emp:
				dotted_manager_user_id = frappe.db.get_value("Employee", dotted_manager_emp, "user_id")
				if dotted_manager_user_id and dotted_manager_user_id == user: 
					dotted_manager_user_email = frappe.db.get_value("User", dotted_manager_user_id, "email")
					if any(row.get("180_days") for row in self.probation_feedback_indifoss):
						if not self.added_dotted_manager_feedback:
							self.added_dotted_manager_feedback = 1
							if dotted_manager_user_email:
								notification_template = frappe.get_doc("Notification", "Dotted Manager to HR For Probation Feedback Form")
								if notification_template:
									subject = frappe.render_template(notification_template.subject, {"doc": self})
									message = frappe.render_template(notification_template.message, {"doc": self})
									frappe.sendmail(
										recipients=[dotted_manager_user_email],
										subject= subject if subject else "Probation Feedback Form Ratting add by Dotted Manager",
										message=message if message else f"This is to inform you that the Probation Feedback Form has been rated by Dotted Manager",
									)
								else:
									frappe.sendmail(
										recipients=[dotted_manager_user_email],
										subject="Probation Feedback Form Ratting add by Dotted Manager",
										message=f"This is to inform you that the Probation Feedback Form has been rated by Dotted Manager",
									)
		except Exception as e:
			frappe.log_error(f"Error updating job applicant status", frappe.get_traceback())
			frappe.throw(f"Error updating job applicant status: {str(e)}")