# Copyright (c) 2025, Jignasha Chavda and contributors
# For license information, please see license.txt

from itertools import groupby


from frappe import _
from prompt_hr.py.leave_application import custom_get_data


import frappe



Filters = frappe._dict

def execute(filters: Filters | None = None) -> tuple:
	if filters.to_date <= filters.from_date:
		frappe.throw(_('"From Date" can not be greater than or equal to "To Date"'))

	columns = get_columns()
	data = custom_get_data(filters)
	charts = get_chart_data(data, filters)
	return columns, data, None, charts



def get_columns() -> list[dict]:
	return [
		{
			"label": _("Leave Type"),
			"fieldtype": "Link",
			"fieldname": "leave_type",
			"width": 200,
			"options": "Leave Type",
		},
		{
			"label": _("Employee"),
			"fieldtype": "Link",
			"fieldname": "employee",
			"width": 100,
			"options": "Employee",
		},
		{
			"label": _("Employee Name"),
			"fieldtype": "Dynamic Link",
			"fieldname": "employee_name",
			"width": 100,
			"options": "employee",
		},
		{
			"label": _("Opening Balance"),
			"fieldtype": "float",
			"fieldname": "opening_balance",
			"width": 150,
		},
		{
			"label": _("New Leave(s) Allocated"),
			"fieldtype": "float",
			"fieldname": "leaves_allocated",
			"width": 200,
		},
		{
			"label": _("Leave(s) Taken"),
			"fieldtype": "float",
			"fieldname": "leaves_taken",
			"width": 150,
		},
		{
			"label": _("Leave(s) Expired"),
			"fieldtype": "float",
			"fieldname": "leaves_expired",
			"width": 150,
		},
		{
			"label": _("Closing Balance"),
			"fieldtype": "float",
			"fieldname": "closing_balance",
			"width": 150,
		},
	]



def get_chart_data(data: list, filters: Filters) -> dict:
	labels = []
	datasets = []
	employee_data = data

	if not data:
		return None

	if data and filters.employee:
		get_dataset_for_chart(employee_data, datasets, labels)

	chart = {
		"data": {"labels": labels, "datasets": datasets},
		"type": "bar",
		"colors": ["#456789", "#EE8888", "#7E77BF"],
	}

	return chart


def get_dataset_for_chart(employee_data: list, datasets: list, labels: list) -> list:
	leaves = []
	employee_data = sorted(employee_data, key=lambda k: k["employee_name"])

	for key, group in groupby(employee_data, lambda x: x["employee_name"]):
		for grp in group:
			if grp.closing_balance:
				leaves.append(
					frappe._dict({"leave_type": grp.leave_type, "closing_balance": grp.closing_balance})
				)

		if leaves:
			labels.append(key)

	for leave in leaves:
		datasets.append({"name": leave.leave_type, "values": [leave.closing_balance]})

