# Copyright (c) 2025, Jignasha Chavda and contributors
# For license information, please see license.txt

import frappe
from frappe.utils import cint, flt
from frappe import _
from hrms.hr.doctype.leave_application.leave_application import get_leaves_for_period
from hrms.hr.report.employee_leave_balance.employee_leave_balance import (
	get_employees,
	get_allocated_and_expired_leaves,
	get_opening_balance,
	get_chart_data
)
import random

Filters = frappe._dict

def execute(filters=None):
	filters = Filters(filters or {})

	# Get filtered leave types
	leave_types = frappe.db.get_all("Leave Type", pluck="name")
	if filters.get("leave_type"):
		leave_types = [filters.get("leave_type")]

	columns = [
		{"label": "Employee", "fieldname": "employee", "fieldtype": "Link", "options": "Employee", "width": 150},
		{"label": "Employee Name", "fieldname": "employee_name", "fieldtype": "Data", "width": 180},
	]

	for lt in leave_types:
		print(lt)
		columns += [
			{"label": f"{lt} (Opening)", "fieldname": f"{lt}_opening", "fieldtype": "Float", "width": 200},
			{"label": f"{lt} (Allocated)", "fieldname": f"{lt}_allocated", "fieldtype": "Float", "width": 200},
			{"label": f"{lt} (Taken)", "fieldname": f"{lt}_taken", "fieldtype": "Float", "width": 200},
			{"label": f"{lt} (Expired)", "fieldname": f"{lt}_expired", "fieldtype": "Float", "width": 200},
			{"label": f"{lt} (Closing)", "fieldname": f"{lt}_closing", "fieldtype": "Float", "width": 200},
		]

	# Prepare data
	data = get_data(filters, leave_types)
	charts = get_chart_data(data, filters)
	return columns, data, None, charts


def get_data(filters, leave_types):
	employees = get_employees(filters)
	precision = cint(frappe.db.get_single_value("System Settings", "float_precision"))
	data = []

	for emp in employees:
		row = {
			"employee": emp.name,
			"employee_name": emp.employee_name,
		}

		for lt in leave_types:
			taken = get_leaves_for_period(emp.name, lt, filters.from_date, filters.to_date) * -1

			allocated, expired, carry_forward = get_allocated_and_expired_leaves(
				filters.from_date, filters.to_date, emp.name, lt
			)

			opening = get_opening_balance(emp.name, lt, filters, carry_forward)
			closing = allocated + opening - (expired + taken)

			# Add dynamic fields to row
			row[f"{lt}_opening"] = flt(opening, precision)
			row[f"{lt}_allocated"] = flt(allocated, precision)
			row[f"{lt}_taken"] = flt(taken, precision)
			row[f"{lt}_expired"] = flt(expired, precision)
			row[f"{lt}_closing"] = flt(closing, precision)

		data.append(row)

	return data


def get_chart_data(data: list, filters: Filters) -> dict:
	if not data or not filters.get("employee"):
		return None

	employee_row = next((row for row in data if row["employee"] == filters["employee"]), None)
	if not employee_row:
		return None

	labels = ["Leave Types"]
	datasets = []
	colors = []

	# Use separate dataset per leave type for multi-color
	for key in employee_row:
		if key.endswith("_closing"):
			leave_type = key.replace("_closing", "")
			if employee_row.get(key, 0) == 0:
				continue
			datasets.append({
				"name": leave_type,
				"values": [employee_row.get(key, 0)]
			})
			colors.append(get_random_color())  # Optional: random color generator or use fixed list

	chart = {
		"data": {
			"labels": labels,
			"datasets": datasets
		},
		"type": "bar",
		"colors": colors,
		"barOptions": {
			"spaceRatio": 0.6,
		},
	}

	return chart


def get_random_color():
	return "#%06x" % random.randint(0, 0xFFFFFF)
