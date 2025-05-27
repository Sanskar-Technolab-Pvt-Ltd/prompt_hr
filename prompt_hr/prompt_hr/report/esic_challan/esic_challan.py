# Copyright (c) 2025, Jignasha Chavda and contributors
# For license information, please see license.txt

import frappe


def execute(filters=None):
	columns, data = get_columns(), get_data(filters)
	return columns, data

def get_columns():
	return [
		{
			"fieldname": "ip_number",
			"label": "IP Number",
			"fieldtype": "Data",
			"width": 150
		},
		{
			"fieldname": "ip_name",
			"label": "IP Name",
			"fieldtype": "Data",
			"width": 200
		},
		{
			"fieldname": "total_no_of_days",
			"label": "No of days for which wages paid/payable during the month",
			"fieldtype": "Data",
			"width": 150
		},
		{
			"fieldname": "total_monthly_wages",
			"label": "Total Monthly Wages",
			"fieldtype": "Currency",
			"width": 150
		},
		{
			"fieldname": "reason",
			"label": "Reason Code for Zero Working Days",
			"fieldtype": "Data",
			"width": 120
		},
		{
			"fieldname":"last_working_day",
			"label": "Last Working Day",
			"fieldtype": "Date",
			"width": 150
		}
	]

def get_data(filters):
	filters.setdefault("docstatus", 1)  # Ensure only submitted Salary Slips are fetched
	data = []
	slip_datas = frappe.get_all(
		"Salary Slip",
		filters=filters,
		fields=[
			"*"
		],
		order_by="creation desc"
	)
	for slip_data in slip_datas:
		row = {}
		employee_number = frappe.get_value("Employee", slip_data.employee, "employee_number")
		row["ip_number"] = employee_number
		row["ip_name"] = frappe.get_value("Employee", slip_data.employee, "employee_name")
		row["total_no_of_days"] = slip_data.total_working_days
		row["total_monthly_wages"] = slip_data.net_pay
		row["reason"] = slip_data.reason_code or ""
		row["last_working_day"] = slip_data.end_date
		data.append(row)

	return data
