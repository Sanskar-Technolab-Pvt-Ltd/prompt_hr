# Copyright (c) 2025, Jignasha Chavda and contributors
# For license information, please see license.txt

import frappe
from frappe.utils import getdate, format_time


def execute(filters=None):
    from_date = filters.get("from_date") or getdate()
    to_date = filters.get("to_date") or getdate()
    columns = [
        {"label": "Employee Number", "fieldname": "employee", "fieldtype": "Link", "options": "Employee", "width": 120},
        {"label": "Employee Name", "fieldname": "employee_name", "fieldtype": "Data", "width": 150},
        {"label": "Job Title", "fieldname": "job_title", "fieldtype": "Data", "width": 120},
        {"label": "Business Unit", "fieldname": "business_unit", "fieldtype": "Data", "width": 100},
        {"label": "Department", "fieldname": "department", "fieldtype": "Link", "options": "Department", "width": 150},
        {"label": "Sub Department", "fieldname": "sub_department", "fieldtype": "Data", "width": 150},
        {"label": "Location", "fieldname": "location", "fieldtype": "Data", "width": 100},
        {"label": "Cost Center", "fieldname": "cost_center", "fieldtype": "Link", "options": "Cost Center", "width": 120},
        {"label": "Reporting Manager", "fieldname": "reports_to", "fieldtype": "Data", "width": 150},
        {"label": "Date", "fieldname": "attendance_date", "fieldtype": "Date", "width": 200},
        {"label": "First Log", "fieldname": "first_log", "fieldtype": "Time", "width": 100},
        {"label": "Last Log", "fieldname": "last_log", "fieldtype": "Time", "width": 100},
        {"label": "Total Effective Hours", "fieldname": "effective_hours", "fieldtype": "Data", "width": 120},
        {"label": "Total Gross Hours", "fieldname": "gross_hours", "fieldtype": "Data", "width": 120},
    ]

    data = []
    attendance_records = frappe.get_all(
        "Attendance",
        filters={
            "docstatus": 1,
            "attendance_date": ["between", [from_date, to_date]],
        },
        fields=[
            "*"
        ],
        order_by="employee, attendance_date",
	)
    print(attendance_records)
    for row in attendance_records:
        employee_data = frappe.get_doc("Employee", row.employee)
        if employee_data.custom_work_location:
            row.custom_work_location = frappe.get_value("Address", employee_data.custom_work_location, "city")
        if employee_data.reports_to:
            row.reports_to = frappe.get_value("Employee", employee_data.reports_to, "employee_name")
        if employee_data:
            row.update({
                "employee_name": employee_data.employee_name,
                "designation": employee_data.designation,
                "custom_business_unit": employee_data.custom_business_unit,
                "department": employee_data.department,
                "custom_subdepartment": employee_data.custom_subdepartment,
                "payroll_cost_center": employee_data.payroll_cost_center,
            })
    for row in attendance_records:
        data.append({
            "employee": row.employee_number,
            "employee_name": row.employee_name,
            "job_title": row.designation,
            "business_unit": row.custom_business_unit,
            "department": row.department,
            "sub_department": row.custom_subdepartment,
            "location": row.custom_work_location,
            "cost_center": row.payroll_cost_center,
            "reports_to": row.reports_to,
            "attendance_date": row.attendance_date,
            "first_log": row.in_time.strftime("%H:%M:%S") if row.in_time else None,
            "last_log": row.out_time.strftime("%H:%M:%S") if row.out_time else None,
            "effective_hours": row.working_hours,
            "gross_hours": 0
        })

    return columns, data
