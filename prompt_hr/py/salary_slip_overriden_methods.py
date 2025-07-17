import frappe
from frappe import _
from collections import defaultdict
from hrms.payroll.doctype.payroll_entry.payroll_entry import log_payroll_failure, get_existing_salary_slips
from frappe.utils import getdate, add_days
from calendar import monthrange
from datetime import datetime
from calendar import monthrange


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

		lop_days_map = defaultdict(float)
		working_days_map = defaultdict(float)
		for emp in payroll_entry.custom_lop_reversal_details:
			lop_days_map[emp.employee] += emp.lop_reversal_days or 0
			working_days_map[emp.employee] = get_working_days_for_month(emp.employee,emp.lop_month)

		# * Remove employees for whom salary slips already exist or are restricted
		employees = list(set(employees) - set(salary_slips_exist_for) - set(restricted_employee))
		for emp in employees:
			if lop_days_map.get(emp) and lop_days_map.get(emp) > 0:
				args.update({"doctype": "Salary Slip", "employee": emp, "custom_lop_days": lop_days_map.get(emp), "custom_working_days_for_lop_reversal": working_days_map.get(emp)})
			else:
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


def get_working_days_for_month(lop_employee, lop_month):
    """
    Given a string like 'April-2025', returns the total_working_days
    from that employees Salary Slip in that month.
    """
    # ? Parse Months using '%B-%Y' (Full month name)
    parsed_date = datetime.strptime(lop_month, "%B-%Y")
    year = parsed_date.year
    month = parsed_date.month

    # * Get start and end date of the month
    start_date = getdate(f"{year}-{month:02d}-01")
    end_day = monthrange(year, month)[1]
    end_date = getdate(f"{year}-{month:02d}-{end_day}")

    # * Fetch Salary Slip for that employee within the given month
    last_month_salary_slip = frappe.get_all(
        "Salary Slip",
        filters={
            "employee": lop_employee,
            "start_date": [">=", start_date],
            "end_date": ["<=", end_date],
            "docstatus": 1,
        },
        fields=["start_date", "total_working_days"],
        limit=1
    )
    # ! If no Salary Slip found, return 0
    if not last_month_salary_slip:
        return end_day

    # * Return the total_working_days from Salary Slip
    return last_month_salary_slip[0].total_working_days
