import frappe
from hrms.payroll.doctype.payroll_entry.payroll_entry import log_payroll_failure, get_existing_salary_slips

def custom_create_salary_slips_for_employees(employees, args, publish_progress=True):
	payroll_entry = frappe.get_cached_doc("Payroll Entry", args.payroll_entry)

	try:

		salary_slips_exist_for = get_existing_salary_slips(employees, args)
		count = 0
		lop_days_map = {emp.employee: emp.custom_lop_reversal_days for emp in payroll_entry.employees}

		employees = list(set(employees) - set(salary_slips_exist_for))
		for emp in employees:
			args.update({"doctype": "Salary Slip", "employee": emp, "custom_lop_days": lop_days_map.get(emp)})
			frappe.get_doc(args).insert()

			count += 1
			if publish_progress:
				frappe.publish_progress(
					count * 100 / len(employees),
					title=_("Creating Salary Slips..."),
				)

		payroll_entry.db_set({"status": "Submitted", "salary_slips_created": 1, "error_message": ""})

		if salary_slips_exist_for:
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
