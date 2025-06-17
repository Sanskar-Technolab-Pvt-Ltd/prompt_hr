import frappe
from frappe import _
from hrms.payroll.doctype.payroll_entry.payroll_entry import log_payroll_failure, get_existing_salary_slips

def custom_create_salary_slips_for_employees(employees, args, publish_progress=True):
	payroll_entry = frappe.get_cached_doc("Payroll Entry", args.payroll_entry)

	# * Get company abbreviation from HR Settings
	prompt_abbr = frappe.db.get_single_value("HR Settings", "custom_prompt_abbr")

	# * Get abbreviation of the company selected in the payroll entry
	company_abbr = frappe.db.get_value("Company", payroll_entry.company, "abbr")

	# * Initialize list to store employees who are restricted (missing info)
	restricted_employee = []

	# ? APPLY RESTRICTION ONLY FOR PROMPT
	if company_abbr == prompt_abbr:
		# * Fetch pending payroll details for the payroll entry
		pending_docs = (
			payroll_entry.custom_remaining_payroll_details
		)

		# * Extract unique employees from the pending records
		restricted_employee = list({
			frappe.get_doc(doc.doctype, doc.name).employee
			for doc in pending_docs
		})

	try:

		salary_slips_exist_for = get_existing_salary_slips(employees, args)
		count = 0
		lop_days_map = {emp.employee: emp.lop_reversal_days for emp in payroll_entry.custom_lop_reversal_details}

		# * Remove employees for whom salary slips already exist or are restricted
		employees = list(set(employees) - set(salary_slips_exist_for) - set(restricted_employee))
		for emp in employees:
			args.update({"doctype": "Salary Slip", "employee": emp, "custom_lop_days": lop_days_map.get(emp)})
			frappe.get_doc(args).insert()

			count += 1
			if publish_progress:
				frappe.publish_progress(
					count * 100 / len(employees),
					title=_("Creating Salary Slips..."),
				)


		if restricted_employee:
			# * Notify about employees with missing bank details or payroll details
			frappe.msgprint(
				_(
					"Salary Slips will not be created for the employees {0} due to missing required details"
				).format(frappe.bold(", ".join(restricted_employee))),
				title=_("Incomplete Employee Information"),
				indicator="blue"
			)
			payroll_entry.db_set({"status": "Draft", "salary_slips_created": 0, "error_message": "", "docstatus": "0", "custom_is_salary_slip_created": 1})

		else:
			payroll_entry.db_set({"status": "Submitted", "salary_slips_created": 1, "error_message": ""})
		
		if salary_slips_exist_for and not restricted_employee:
			frappe.msgprint(
				_(
					"Salary Slips already exist for employees {}, and will not be processed by this payroll."
				).format(frappe.bold(", ".join(emp for emp in salary_slips_exist_for))),
				title=_("Message"),
				indicator="orange",
			)

	except Exception as e:
		frappe.db.rollback()
		log_payroll_failure("creation", payroll_entry, e)

	finally:
		frappe.db.commit()
		frappe.publish_realtime("completed_salary_slip_creation", user=frappe.session.user)
