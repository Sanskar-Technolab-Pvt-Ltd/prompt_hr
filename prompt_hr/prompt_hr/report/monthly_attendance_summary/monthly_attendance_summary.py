# Copyright (c) 2025, Jignasha Chavda and contributors
# For license information, please see license.txt

import frappe
from frappe import _
from frappe.query_builder.functions import Extract
from frappe.utils import cstr
from frappe.utils.nestedset import get_descendants_of
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
    get_attendance_status_for_detailed_view,
    get_attendance_status_for_summarized_view,
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
		if d.status == "On Leave":
			if d.leave_type:
				leave_abbr = frappe.get_doc("Leave Type",d.leave_type).custom_leave_type_abbr
			leave_map.setdefault(d.employee, {}).setdefault(d.shift, []).append([d.day_of_month, d.leave_type])
			continue

		if d.shift is None:
			d.shift = ""

		attendance_map.setdefault(d.employee, {}).setdefault(d.shift, {})
		attendance_map[d.employee][d.shift][d.day_of_month] = d.status

	# leave is applicable for the entire day so all shifts should show the leave entry
	for employee, leave_days in leave_map.items():
		for assigned_shift, days in leave_days.items():
			# no attendance records exist except leaves
			if employee not in attendance_map:
				attendance_map.setdefault(employee, {}).setdefault(assigned_shift, {})

			for day in days:
				for shift in attendance_map[employee].keys():
					attendance_map[employee][shift][day[0]] = day[1]

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
	"""Returns list of shift-wise attendance status for employee
	[
	        {'shift': 'Morning Shift', 1: 'A', 2: 'P', 3: 'A'....},
	        {'shift': 'Evening Shift', 1: 'P', 2: 'A', 3: 'P'....}
	]
	"""
	total_days = get_total_days_in_month(filters)
	attendance_values = []

	for shift, status_dict in employee_attendance.items():
		row = {"shift": shift}

		for day in range(1, total_days + 1):
			status = status_dict.get(day)
			if status is None and holidays:
				status = get_holiday_status(day, holidays)

			default_status = ""
			if status in frappe.get_all("Leave Type", fields=["leave_type_name"],pluck="leave_type_name"):
				default_status = "L"
			abbr = get_status_map().get(status, default_status)
			row[cstr(day)] = abbr

		attendance_values.append(row)

	return attendance_values

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
