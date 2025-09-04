# Copyright (c) 2025, Jignasha Chavda and contributors
# For license information, please see license.txt

import frappe
from frappe import _
from frappe.query_builder.functions import Extract
from frappe.utils import cstr, cint
from frappe.utils.nestedset import get_descendants_of
from calendar import monthrange
from datetime import date
from hrms.hr.report.monthly_attendance_sheet.monthly_attendance_sheet import (
    get_attendance_map,
    get_columns,
    get_chart_data,
    get_employee_related_details,
    get_holiday_map,
    get_total_days_in_month,
    get_holiday_status,
    get_leave_summary,
    get_entry_exits_summary,
    set_defaults_for_summarized_view,
    get_attendance_summary_and_days,
)

Filters = frappe._dict

def get_status_map():
	status_map = {
		"Present": "P",
		"Absent": "A",
		"Half Day": "HD",
		"Work From Home": "WFH",
		"On Leave": "L",
		"Holiday": "H",
		"Weekly Off": "WO",
	}
	leave_types = frappe.get_all("Leave Type", fields=["leave_type_name", "custom_leave_type_abbr"])
	for leave_type in leave_types:
		if leave_type.custom_leave_type_abbr:
			status_map.update({leave_type.leave_type_name:leave_type.custom_leave_type_abbr})
	return status_map

day_abbr = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]

def execute(filters: Filters | None = None) -> tuple:
	filters = frappe._dict(filters or {})

	if not (filters.month and filters.year):
		frappe.throw(_("Please select month and year."))

	if not filters.company:
		frappe.throw(_("Please select company."))

	if filters.company:
		filters.companies = [filters.company]
		if filters.include_company_descendants:
			filters.companies.extend(get_descendants_of("Company", filters.company))

	attendance_map = get_attendance_map(filters)
	attendance_map_with_leave_types = get_attendance_map_with_leave_type(filters)
	if not attendance_map:
		frappe.msgprint(_("No attendance records found."), alert=True, indicator="orange")
		return [], [], None, None

	columns = get_columns(filters)
	
	# ? ADD MORE COLUMNS FOR SUMMARIZED VIEW
	if filters.summarized_view:
		columns.insert(2, 
			{
					"label": _("Total Working Days"),
					"fieldname": "total_working_days",
					"fieldtype": "Float",
					"width": 150,
			},
		)
		columns.insert(3, 
			{
					"label": _("Total LOP Days"),
					"fieldname": "total_lop_days",
					"fieldtype": "Float",
					"width": 150,
			},
		)
		columns.insert(4, 
			{
					"label": _("Total Payment Days"),
					"fieldname": "total_payment_days",
					"fieldtype": "Float",
					"width": 150,
			},
		)
	else:
		columns.append(
			{
					"label": _("Total Working Days"),
					"fieldname": "total_working_days",
					"fieldtype": "Float",
					"width": 150,
			},
		)
		columns.append(
			{
					"label": _("Total LOP Days"),
					"fieldname": "total_lop_days",
					"fieldtype": "Float",
					"width": 150,
			},
		)
		columns.append(
			{
					"label": _("Total Payment Days"),
					"fieldname": "total_payment_days",
					"fieldtype": "Float",
					"width": 150,
			},
		)
	# * Apply width increase: 50 for all, 100 for 'employee'
	columns = increase_column_widths(
		columns,
		default_increment=50,
		special_cases={"employee": 150}
	)
	data = get_data(filters, attendance_map_with_leave_types)

	if not data:
		frappe.msgprint(_("No attendance records found for this criteria."), alert=True, indicator="orange")
		return columns, [], None, None

	message = get_message() if not filters.summarized_view else ""
	chart = get_chart_data(attendance_map, filters)

	return columns, data, message, chart

def get_attendance_map_with_leave_type(filters):
	attendance_list = get_attendance_records(filters)
	attendance_map = {}
	leave_map = {}

	for d in attendance_list:
		day = d.day_of_month
		# * Handle leave status
		if d.status == "On Leave":
			leave_type_name = frappe.get_value("Leave Type", d.leave_type, "leave_type_name") or d.leave_type
			leave_map.setdefault(d.employee, {})[day] = leave_type_name
			continue

		# * Handle present, absent, etc.
		attendance_map.setdefault(d.employee, {})[day] = d.status

	# * Apply leave status only if day not already marked in attendance_map
	for employee, leave_days in leave_map.items():
		attendance_map.setdefault(employee, {})
		for day, leave_type_name in leave_days.items():
			if day not in attendance_map[employee]:
				attendance_map[employee][day] = leave_type_name
	return attendance_map


def get_message() -> str:
	message = ""
	colors = ["green", "red", "orange", "green", "#318AD8", "", ""]
	status_map = get_status_map()
	count = 0
	for status, abbr in status_map.items():
		message += f"""
			<span style='border-left: 2px solid {colors[count%len(colors)]}; padding-right: 12px; padding-left: 5px; margin-right: 3px;'>
				{status} - {abbr}
			</span>
		"""
		count += 1

	return message

def get_data(filters: Filters, attendance_map: dict) -> list[dict]:
	employee_details, group_by_param_values = get_employee_related_details(filters)
	holiday_map = get_holiday_map(filters)
	data = []

	if filters.group_by:
		group_by_column = frappe.scrub(filters.group_by)

		for value in group_by_param_values:
			if not value:
				continue

			records = get_rows(employee_details[value], filters, holiday_map, attendance_map)

			if records:
				data.append({group_by_column: value})
				data.extend(records)
	else:
		data = get_rows(employee_details, filters, holiday_map, attendance_map)

	return data


def get_attendance_records(filters: Filters) -> list[dict]:
	Attendance = frappe.qb.DocType("Attendance")
	query = (
		frappe.qb.from_(Attendance)
		.select(
			Attendance.employee,
			Extract("day", Attendance.attendance_date).as_("day_of_month"),
			Attendance.status,
			Attendance.shift,
			Attendance.leave_type
		)
		.where(
			(Attendance.docstatus == 1)
			& (Attendance.company.isin(filters.companies))
			& (Extract("month", Attendance.attendance_date) == filters.month)
			& (Extract("year", Attendance.attendance_date) == filters.year)
		)
	)

	if filters.employee:
		query = query.where(Attendance.employee == filters.employee)
	query = query.orderby(Attendance.employee, Attendance.attendance_date)

	return query.run(as_dict=1)


def get_attendance_status_for_detailed_view(
	employee: str, filters: Filters, employee_attendance: dict, holidays: list
) -> list[dict]:

	# ? CALCULATE TOTAL DAYS IN THE SELECTED MONTH
	total_days = get_total_days_in_month(filters)
	row = {}
	status_map = get_status_map()

	# ? INITIALIZE WORKING DAYS, LOSS OF PAY (LOP) DAYS, AND PAYMENT DAYS
	total_working_days = 0
	total_lop_days = 0
	total_payment_days = 0
	year = cint(filters.year)
	month = cint(filters.month)

	# * GET FIRST AND LAST DATE OF THE MONTH
	start_date = date(year, month, 1)
	end_date = date(year, month, monthrange(year, month)[1])

	# ? DETERMINE WHETHER TO INCLUDE HOLIDAYS IN TOTAL WORKING DAYS
	include_holiday = frappe.db.get_single_value("Payroll Settings", "include_holidays_in_total_working_days")
	if include_holiday:
		total_working_days = total_days
	else:
		# ! THROW ERROR IF HOLIDAYS LIST IS MISSING
		if not holidays:
			frappe.throw(
				_("Please set default holidays list for company {}").format(filters.company),
				title=_("Missing Default Holidays List"),
			)
		total_working_days = total_days - len(holidays)

	# ? FETCH ATTENDANCE RECORDS FOR EMPLOYEE IN THE SPECIFIED MONTH
	attendance_record = frappe.get_all(
		"Attendance",
		fields=["name", "leave_type", "status"],
		filters={
			"employee": employee,
			"company": filters.company,
			"docstatus": 1,
			"attendance_date": ["between", [start_date, end_date]],
		},
	)

	# ? LOOP THROUGH ATTENDANCE RECORDS TO CALCULATE LOP DAYS
	if attendance_record:
		for record in attendance_record:
			if record.leave_type:
				leave_type = frappe.get_doc("Leave Type", record.leave_type)
				if leave_type.is_lwp:
					if record.status == "Half Day":
						total_lop_days += 0.5  # * ADD HALF DAY FOR HALF-DAY LEAVE
					else:
						total_lop_days += 1  # * ADD FULL DAY FOR FULL-DAY LEAVE
	
	# ? BUILD DAILY STATUS MAP USING ABBREVIATIONS
	for day in range(1, total_days + 1):
		status = employee_attendance.get(day)
		if status is None and holidays:
			status = get_holiday_status(day, holidays)
		abbr = status_map.get(status, "")
		row[cstr(day)] = abbr
	
	# ? GET PENALTY LOPS FROM EMPLOYEE PENALTY
	employee_penalty = frappe.get_list(
		"Employee Penalty",
		fields=["deduct_leave_without_pay"],
		filters={
			"employee": employee,
			"company": filters.company,
			"penalty_date": ["between", [start_date, end_date]],
			"is_leave_balance_restore":0
		},
	)
	penalty_lops = 0
	if employee_penalty:
		penalty_lops = sum([d.deduct_leave_without_pay for d in employee_penalty])

	# ? ADD PENALTY LOPS TO TOTAL LOPS
	total_lop_days += penalty_lops

	# ? CALCULATE PAYMENT DAYS BASED ON WORKING DAYS AND LOP DAYS
	if total_lop_days > total_working_days:
		total_payment_days = 0  # ! LOP EXCEEDS WORKING DAYS, ZERO PAYMENT DAYS
	else:
		total_payment_days = total_working_days - total_lop_days

	# * FINAL SUMMARY FIELDS
	row["total_working_days"] =  total_working_days
	row["total_lop_days"] = total_lop_days
	row["total_payment_days"] = total_payment_days

	return [row]

def get_rows(employee_details: dict, filters: Filters, holiday_map: dict, attendance_map: dict) -> list[dict]:
	records = []
	default_holiday_list = frappe.get_cached_value("Company", filters.company, "default_holiday_list")

	for employee, details in employee_details.items():
		emp_holiday_list = details.holiday_list or default_holiday_list
		holidays = holiday_map.get(emp_holiday_list)

		if filters.summarized_view:
			attendance = get_attendance_status_for_summarized_view(employee, filters, holidays)
			if not attendance:
				continue

			leave_summary = get_leave_summary(employee, filters)
			entry_exits_summary = get_entry_exits_summary(employee, filters)

			row = {"employee": employee, "employee_name": details.employee_name}
			set_defaults_for_summarized_view(filters, row)
			row.update(attendance)
			row.update(leave_summary)
			row.update(entry_exits_summary)

			records.append(row)
		else:
			employee_attendance = attendance_map.get(employee)
			if not employee_attendance:
				continue

			attendance_for_employee = get_attendance_status_for_detailed_view(
				employee, filters, employee_attendance, holidays
			)
			# set employee details in the first row
			attendance_for_employee[0].update({"employee": employee, "employee_name": details.employee_name})

			records.extend(attendance_for_employee)

	return records

def get_attendance_status_for_summarized_view(employee: str, filters: Filters, holidays: list) -> dict:
	"""Returns dict of attendance status for employee like
	{'total_working_days':30, 'total_lop_days':1, 'total_payement_days':29, total_present': 1.5, 'total_leaves': 0.5, 'total_absent': 13.5, 'total_holidays': 8, 'unmarked_days': 5}
	"""
	summary, attendance_days = get_attendance_summary_and_days(employee, filters)
	if not any(summary.values()):
		return {}

	total_days = get_total_days_in_month(filters)
	total_holidays = total_unmarked_days = 0
	total_working_days = 0
	total_lop_days = 0
	total_payment_days = 0

	year = cint(filters.year)
	month = cint(filters.month)

	start_date = date(year, month, 1)
	end_date = date(year, month, monthrange(year, month)[1])

	include_holiday = frappe.db.get_single_value("Payroll Settings", "include_holidays_in_total_working_days")
	if include_holiday:
		total_working_days = total_days
	else:
		if not holidays:
			frappe.throw(
				_("Please set default holidays list for company {}").format(filters.company),
				title=_("Missing Default Holidays List"),
			)
		total_working_days = total_days - len(holidays)

	attendance_record = frappe.get_all(
		"Attendance",
		fields=["name", "leave_type", "status"],
		filters={
			"employee": employee,
			"company": filters.company,
			"docstatus": 1,
			"attendance_date": ["between", [start_date, end_date]],
		},
	)
	if attendance_record:
		for record in attendance_record:
			if record.leave_type:
				leave_type = frappe.get_doc("Leave Type", record.leave_type)
				if leave_type.is_lwp:
					if record.status == "Half Day":
						total_lop_days += 0.5
					else:
						total_lop_days+=1

	for day in range(1, total_days + 1):
		if day in attendance_days:
			continue

		status = get_holiday_status(day, holidays)
		if status in ["Weekly Off", "Holiday"]:
			total_holidays += 1
		elif not status:
			total_unmarked_days += 1

	if total_lop_days > total_working_days:
		total_payment_days = 0
	else:
		total_payment_days = total_working_days - total_lop_days
	return {
		"total_working_days": total_working_days,
		"total_lop_days":total_lop_days,
		"total_payment_days":total_payment_days,
		"total_present": summary.total_present + summary.total_half_days,
		"total_leaves": summary.total_leaves + summary.total_half_days,
		"total_absent": summary.total_absent,
		"total_holidays": total_holidays,
		"unmarked_days": total_unmarked_days,
	}

# * Increase all column widths by a given increment, with special cases
def increase_column_widths(columns, default_increment=50, special_cases=None):
    if special_cases is None:
        special_cases = {}

    for col in columns:
        fieldname = col.get("fieldname", "")
        current_width = col.get("width", 100)

        # * Use custom increment if it's a special case
        increment = special_cases.get(fieldname, default_increment)
        col["width"] = current_width + increment

    return columns
