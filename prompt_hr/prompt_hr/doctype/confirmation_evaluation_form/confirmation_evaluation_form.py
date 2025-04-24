# Copyright (c) 2025, Jignasha Chavda and contributors
# For license information, please see license.txt

import frappe
from frappe.utils import today, add_days
from frappe.model.document import Document


class ConfirmationEvaluationForm(Document):
	
	def validate(self):
		
		try:
			if self.company == "Prompt Equipments PVT LTD":
				
				
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
							users = frappe.db.get_all("Has Role", filters={"role": "HR Manager"}, fields=["parent"])
							if users:
								for user in users:
									hr_employee = frappe.db.exists("Employee", {"user_id": user.parent, "company": "Prompt Equipments PVT LTD"})
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
		
				
				
		except Exception as e:
			frappe.log_error(frappe.get_traceback(), "Error in Confirmation Evaluation Form")
			frappe.throw("An error occurred during validation. Please check the logs.")
	
	# def probation_status(self):
	# 	try:
	# 		print(f"\n\n Printing \n\n")
	# 		#* CALCULATING THE LAST DATE OF WORK FROM THE DATE WHEN PROBATION STATUS IS SET TO TERMINATE TO BASED ON THE NOTICE PERIOD DAYS
	# 		if self.probation_status == "Terminate" and not self.last_work_date:
	# 			notice_period_days = frappe.db.get_value("Employee", {"name": self.employee}, "notice_number_of_days")

	# 			if self.last_work_date:
	# 				self.last_work_date = add_days(today(), notice_period_days)
	# 			else:
	# 				frappe.throw("Please enter the notice period days.")
	# 	except Exception as e:
	# 		frappe.log_error(frappe.get_traceback(), "Error in Confirmation Evaluation Form")
	# 		frappe.throw("An error occurred while calculating the probation status. Please check the logs.")