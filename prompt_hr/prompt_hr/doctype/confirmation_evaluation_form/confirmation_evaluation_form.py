# Copyright (c) 2025, Jignasha Chavda and contributors
# For license information, please see license.txt

import frappe
from frappe.utils import today, add_days
from frappe.model.document import Document
from prompt_hr.utils import get_next_date, convert_month_to_days

class ConfirmationEvaluationForm(Document):
	
	def validate(self):
		
		try:
			# * IF COMPANY IS PROMPT
			company_abbr = frappe.db.get_single_value("HR Settings", "custom_prompt_abbr")
			if company_abbr:
				company_id = frappe.db.get_value("Company", {"abbr": company_abbr}, "name")
				if company_id:
					if self.company == company_id:
						
						
					#* CHECKING IF THE REPORTING HEAD OR DEPARTMENT OF HEAD HAS ENTERED THE RATING 
						user = frappe.session.user
						user_employee = frappe.db.get_value("Employee", {"user_id": user}, "name") or None
						is_reporting_head = True if (self.reporting_manager and user_employee) and user_employee == self.reporting_manager else False
						is_head_of_department = True if (self.hod and user_employee) and user_employee == self.hod else False
						
						if (is_reporting_head or is_head_of_department) and (self.table_txep and len(self.table_txep) > 0):
							
							if is_reporting_head:
								
								if any(row.rh_rating not in ["", None, 0.0, 0] for row in self.table_txep):
									self.rh_rating_added = 1
								else:
									self.rh_rating_added = 0
							elif is_head_of_department:
								
								if any(row.dh_rating not in ["", None, 0.0, 0] for row in self.table_txep):
									self.dh_rating_added = 1
			
								#* IF THE HEAD OF DEPARTMENT HAS ENTERED THE RATING THEN SEND EMAIL TO HR MANAGER
									users = frappe.db.get_all("Has Role", filters={"role": "S - HR Director (Global Admin)", "parenttype": "User"}, fields=["parent"])
									if users:
										for user in users:
											hr_employee = frappe.db.exists("Employee", {"user_id": user.parent, "company": company_id, "status": "Active"})
											if hr_employee:
												user_email = frappe.db.get_value("User", {"name": user.parent}, "email")
												if user_email:
													
													notification_template = frappe.get_doc("Notification", "Confirmation Remarks For HR")
													subject = frappe.render_template(notification_template.subject, {"doc": self})
													message = frappe.render_template(notification_template.message, {"doc": self})
						
													frappe.sendmail(
														recipients=[user_email],
														subject=subject,
														message=message
													)
								else:
									self.dh_rating_added = 0
				
				else:
					frappe.throw(f"No Company found for abbreviation {company_abbr}")
			else:
				# frappe.log_error(frappe.get_traceback(), "Error in Confirmation Evaluation Form")
				frappe.throw("No Company Abbreviation found for Prompt Company, Please set Company Abbreviation in HR Settings")
		except Exception as e:
			frappe.log_error(frappe.get_traceback(), "Error in Confirmation Evaluation Form")
			frappe.throw(f"{str(e)}")

	def on_submit(self):
		"""Method to add Confirmation Evaluation Data to Employee if company  equals to Prompt Equipments PVT LTD when Confirmation Evaluation Form is submitted.
    """
		try:
			company_abbr = frappe.db.get_single_value("HR Settings", "custom_prompt_abbr")

			if company_abbr:
				company_id = frappe.db.get_value("Company", {"abbr": company_abbr}, "name")
				if company_id:
					if self.employee and self.company == company_abbr:
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

				else:
					frappe.throw(f"No Company found for Abbreviation {company_abbr}")
			else:
				frappe.throw(f"Company Abbreviation for Prompt Not found, Please set Company Abbreviation for Prompt")
    
		except Exception as e:
			frappe.log_error(f"Error updating job applicant status", frappe.get_traceback())
			frappe.throw(f"Error updating job applicant status: {str(e)}")
	