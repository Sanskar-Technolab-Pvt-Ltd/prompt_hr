# Copyright (c) 2025, Jignasha Chavda and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document
from frappe import _
from frappe.utils import nowdate


class ExitApprovalProcess(Document):
	pass

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
			for act in activities:
				separation.append("activities", act)

		separation.insert(ignore_permissions=True)
		frappe.db.commit()

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
