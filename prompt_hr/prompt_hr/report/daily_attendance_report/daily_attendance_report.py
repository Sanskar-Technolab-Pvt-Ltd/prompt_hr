# Copyright (c) 2025, Jignasha Chavda and contributors
# For license information, please see license.txt

import frappe
from frappe.utils import format_time


def execute(filters=None):
    
    
    
	columns = get_columns()
	data = get_data(filters)

	return columns, data


def get_columns():
    
    columns = [
		{
			"label": "Employee ID",
			"fieldname": "employee",
			"fieldtype": "Link",
			"options": "Employee"
		},
		{
			"label": "Employee Name",
			"fieldname": "employee_name",
			"fieldtype": "Data",
		},
		{
			"label": "Date",
			"fieldname": "date",
			"fieldtype": "Date",
		},
		{
			"label": "In Time",
			"fieldname": "in_time",
			"fieldtype": "Time",
			"width": 200
		},
		{
			"label": "Out Time",
			"fieldname": "out_time",
			"fieldtype": "Time",
			"width": 200
		},
		{
			"label": "Status",
			"fieldname": "status",
			"fieldtype": "Data",
		},
		{
			"label": "Working Hours",
			"fieldname": "working_hours",
			"fieldtype": "Float",
		},
		{
			"label": "Shift",
			"fieldname": "shift",
			"fieldtype": "Link",
			"options": "Shift Type"
		},
		{
			"label": "Employee Penalty Record",
			"fieldname": "employee_penalty_record",
			"fieldtype": "Link",
			"options": "Employee Penalty"
		},
		
	]        
    return columns


def get_data(filters=None):
    filters = frappe._dict(filters or {})

    employee_filter = {"status": "Active"}
    if filters.employee:
        employee_filter["name"] = filters.employee

    employees = frappe.db.get_all("Employee", filters=employee_filter, fields=["name as employee", "employee_name"])

    employee_data = []

    for emp in employees:
        row = {
            "employee": emp.employee,
            "employee_name": emp.employee_name,
            "date": filters.attendance_date or ""
        }

        checkin_filters = {"employee": emp.employee, "log_type": "IN"}
        checkout_filters = {"employee": emp.employee, "log_type": "OUT"}

        if filters.attendance_date:
            start_datetime = f"{filters.attendance_date} 00:00:00"
            end_datetime = f"{filters.attendance_date} 23:59:59"

            checkin_filters["time"] = ["between", [start_datetime, end_datetime]]
            checkout_filters["time"] = ["between", [start_datetime, end_datetime]]

        in_checkin = frappe.db.get_all("Employee Checkin", filters=checkin_filters, fields=["time"], limit=1, order_by="time asc")
        if in_checkin:
            row["in_time"] = format_time(in_checkin[0].time, "HH:mm:ss")


        out_checkin = frappe.db.get_all("Employee Checkin", filters=checkout_filters, fields=["time"], limit=1, order_by="time desc")
        if out_checkin:
            row["out_time"] = format_time(out_checkin[0].time, "HH:mm:ss")


        att_filters = {"employee": emp.employee}
        
        if filters.attendance_date:
            att_filters["attendance_date"] = filters.attendance_date
        if filters.status:
            att_filters["status"] = filters.status

        attendance_data = frappe.db.get_all("Attendance", filters=att_filters, fields=["status", "working_hours", "custom_employee_penalty_id as employee_penalty_record"],limit=1)
        
        if attendance_data:
            att = attendance_data[0]
            row["status"] = att.status or ""
            row["working_hours"] = att.working_hours or ""
            row["employee_penalty_record"] = att.employee_penalty_record or ""

        if filters.status and not attendance_data:
            continue
        employee_data.append(row)
    return employee_data