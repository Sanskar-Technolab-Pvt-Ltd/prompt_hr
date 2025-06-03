# Copyright (c) 2025, Jignasha Chavda and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document
from frappe import _
from frappe.utils import nowdate
import frappe.utils
from prompt_hr.py.utils import send_notification_email, get_hr_managers_by_company,get_prompt_company_name,get_indifoss_company_name


class ExitApprovalProcess(Document):
	def on_update(self):
		# ? CHECK IF RESIGNATION_APPROVAL CHANGED TO "APPROVED"
		if self.resignation_approval == "Approved" and frappe.db.get_value("Employee", self.employee, "relieving_date") != self.last_date_of_working:
			if self.last_date_of_working:
				frappe.db.set_value("Employee", self.employee, "relieving_date", self.last_date_of_working)


# ? FUNCTION TO AUTO CREATE EMPLOYEE SEPARATION RECORD
@frappe.whitelist()
def raise_exit_checklist(employee, company):
	try:
		# ? CHECK IF EMPLOYEE SEPARATION RECORD ALREADY EXISTS
		if frappe.db.exists("Employee Separation", {"employee": employee}):
			return {
				"status": "info",
				"message": _("Employee Separation record already exists.")
			}

		# ? FETCH EMPLOYEE DETAILS
		employee_details = frappe.db.get_value(
			"Employee", employee, ["designation", "department", "grade"], as_dict=True
		)
		if not employee_details:
			return {
				"status": "error",
				"message": _("Employee not found.")
			}

		# ? FETCH EMPLOYEE SEPARATION TEMPLATE
		templates = frappe.get_all(
			"Employee Separation Template",
			filters={
				"company": company,
				"designation": ["in", [employee_details.designation, ""]],
				"department": ["in", [employee_details.department, ""]],
				"employee_grade": ["in", [employee_details.grade, ""]]
			},
			fields=["name"],
			limit=1
		)
		employee_separation_template = templates[0]["name"] if templates else None

		# ? CREATE EMPLOYEE SEPARATION RECORD
		separation = frappe.new_doc("Employee Separation")
		separation.employee = employee
		separation.company = company
		separation.boarding_begins_on = nowdate()

		# ? ASSIGN TEMPLATE AND ACTIVITIES
		if employee_separation_template:
			separation.employee_separation_template = employee_separation_template
			activities = frappe.get_all(
				"Employee Boarding Activity",
				filters={"parent": employee_separation_template},
				fields=[
					"activity_name", "custom_checklist_name", "custom_checklist_record", "role", "user",
					"custom_is_submitted", "custom_is_raised", "task", "task_weight",
					"required_for_employee_creation", "duration", "begin_on", "custom_raised_on",
					"custom_is_sent", "description", "custom_email_description"
				]
			)

			recipients = []
			for act in activities:
				recipients.append(act.user)
				separation.append("activities", act)
			
			recipients += get_hr_managers_by_company(company)
			recipients = list(set(recipients)) 
			

		separation.insert(ignore_permissions=True)
		frappe.db.commit()
		send_notification_email(doctype="Employee Separation", docname=separation.name, recipients=recipients, notification_name="Employee Separation Notification")

		return {
				"status": "success",
				"message": _("Employee Separation record created successfully.")
			}


	except frappe.ValidationError as ve:
		frappe.log_error(frappe.get_traceback(), "Validation Error in raise_exit_checklist")
		return {
			"status": "error",
			"message": _("Validation error: {0}").format(str(ve))
		}

	except Exception as e:
		frappe.log_error(frappe.get_traceback(), "Error in raise_exit_checklist")
		return {
			"status": "error",
			"message": _("An unexpected error occurred: {0}").format(str(e))
		}

# ? FUNCTION TO RAISE EXIT INTERVIEW
@frappe.whitelist()
def raise_exit_interview(employee, company, exit_approval_process):
	try:
		# ? CHECK IF EXIT INTERVIEW RECORD ALREADY EXISTS
		if frappe.db.exists("Exit Interview", {"employee": employee}):
			return {
				"status": "info",
				"message": _("Exit Interview record already exists.")
			}

		# ? DETERMINE QUIZ NAME BASED ON COMPANY
		if company == get_prompt_company_name().get("company_name"):
			quiz_name = frappe.db.get_value("HR Settings", None, "custom_exit_quiz_at_employee_form_for_prompt")
		elif company == get_indifoss_company_name().get("company_name"):
			quiz_name = frappe.db.get_value("HR Settings", None, "custom_exit_quiz_at_employee_form_for_indifoss")
		else:
			frappe.throw(_("Company not recognized or quiz not configured."))

		if not quiz_name:
			frappe.throw(_("Exit quiz not configured for this company."))

		# ? CREATE EXIT INTERVIEW RECORD
		exit_interview = frappe.new_doc("Exit Interview")
		exit_interview.employee = employee
		exit_interview.company = company
		exit_interview.date = nowdate()
		exit_interview.custom_resignation_quiz = quiz_name
		exit_interview.insert(ignore_permissions=True)
		frappe.db.commit()

		# ? SEND EXIT INTERVIEW NOTIFICATION
		send_exit_interview_notification(employee, exit_interview.name)
		# ? LINK EXIT INTERVIEW TO EMPLOYEE SEPARATION
		frappe.db.set_value("Exit Approval Process", exit_approval_process, "exit_interview", exit_interview.name)
		frappe
		return {
			"status": "success",
			"message": _("Exit Interview record created successfully."),
			"exit_interview": exit_interview.name
		}

	except Exception as e:
		frappe.log_error(frappe.get_traceback(), "Error in create_exit_interview")
		return {
			"status": "error",
			"message": _("Failed to create Exit Interview: {0}").format(str(e))
		}

# ? FUNCTION TO SEND EXIT INTERVIEW NOTIFICATION
@frappe.whitelist()
def send_exit_interview_notification(employee, exit_interview_name):
	try:
		# ? GET USER ID
		user_id = frappe.db.get_value("Employee", employee, "user_id")
		if not user_id:
			frappe.throw(_("User ID (email) not found for this employee."))

		# ? SEND EMAIL
		send_notification_email(
			doctype="Exit Interview",
			docname=exit_interview_name,
			recipients=[user_id],
			notification_name="Exit Questionnaire Mail To Employee",
			button_link=frappe.utils.get_url() + "/exit-questionnaire/new"
		)

		return {
			"status": "success",
			"message": _("Exit Interview email sent successfully.")
		}

	except Exception as e:
		frappe.log_error(frappe.get_traceback(), "Error in send_exit_interview_notification")
		return {
			"status": "error",
			"message": _("Failed to send email: {0}").format(str(e))
		}
