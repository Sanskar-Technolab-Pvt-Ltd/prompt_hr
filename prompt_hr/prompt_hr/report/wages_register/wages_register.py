# Copyright (c) 2025, Jignasha Chavda and contributors
# For license information, please see license.txt

import frappe
from frappe.utils import getdate, get_datetime
import calendar


def execute(filters=None):
    columns = get_columns()
    data = get_data(filters)
    return columns, data

def get_columns():
    # Static columns
    columns = [
        {"label": "Employee", "fieldname": "employee_name", "fieldtype": "Data", "width": 150},
        {"label": "Father/Husband Name", "fieldname": "guardian_name", "fieldtype": "Data", "width": 150},
        {"label": "Designation", "fieldname": "designation", "fieldtype": "Data", "width": 120},
        {"label": "Minimum Rate of Wages Payable", "fieldname": "min_wages", "fieldtype": "Currency", "width": 120},
        {"label": "Attendance", "fieldname": "attendance", "fieldtype": "Float", "width": 80},
        {"label": "Overtime", "fieldname": "overtime", "fieldtype": "Float", "width": 80},
        {"label": "Gross Wages", "fieldname": "gross_wages", "fieldtype": "Currency", "width": 120},
    ]
    # Dynamically add salary components as columns
    dynamic_components = frappe.get_all(
        "Salary Component",
        filters={"disabled": 0},
        fields=["name"]
    )
    for comp in dynamic_components:
        columns.append({
            "label": comp.name,
            "fieldname": comp.name.lower().replace(" ", "_"),
            "fieldtype": "Currency",
            "width": 120
        })
    # Add deduction columns
    columns += [
        {"label": "Total Income Tax", "fieldname": "total_income_tax", "fieldtype": "Currency", "width": 120},
        {"label": "Total Deductions", "fieldname": "total_deductions", "fieldtype": "Currency", "width": 120},
        {"label": "Net Pay", "fieldname": "net_pay", "fieldtype": "Currency", "width": 120},
        {"label": "Date of Payment", "fieldname": "payment_date", "fieldtype": "Date", "width": 120},
        {"label": "Signature/Thumb impression of employee", "fieldname": "signature", "fieldtype": "Data", "width": 120}
    ]
    return columns

def get_data(filters):
    month = frappe.utils.getdate(filters.get("month")).month
    year = int(get_datetime().year)
    from_date = getdate(f"{year}-{month}-01")
    last_day = calendar.monthrange(year, month)[1]
    to_date = getdate(f"{year}-{month}-{last_day}")
    # Fetch Salary Slips for the period
    slips = frappe.get_all(
        "Salary Slip",
        filters={"start_date": from_date, "end_date":to_date, "docstatus":1},
        fields=["name", "employee_name", "employee", "designation",  "gross_pay", "total_deduction", "net_pay", "payment_days"]
    )
    data = []
    threshold_hours = frappe.db.get_single_value("HR Settings", "standard_working_hours") or 8
    for slip in slips:
        # Fetch all attendance records where overtime is possible
        attendance_records = frappe.get_all("Attendance",
            fields=["name", "employee", "employee_name", "attendance_date", "in_time", "out_time", "working_hours","custom_overtime"],
            filters={"docstatus": 1,"employee":slip.employee, "status": "Present","attendance_date": ["between", [from_date, to_date]]},
            order_by="employee_name, attendance_date"
        )
        overtime = 0
        for att in attendance_records:
            overtime += att.custom_overtime

        row = {
            "employee_name": slip.employee_name,
            "guardian_name": frappe.get_value("Employee",slip.employee, "middle_name"),
            "designation": slip.designation,
            "attendance": slip.payment_days,
            "overtime": overtime,
            "gross_wages": slip.gross_pay,
            "total_income_tax": slip.total_income_tax or 0,
            "total_deductions": slip.total_deduction,
            "net_pay": slip.net_pay,
            "payment_date": frappe.utils.getdate(slip.posting_date),
            "signature": slip.employee_name,
        }
        # Fetch dynamic salary components for each slip
        components = frappe.get_all(
            "Salary Detail",
            filters={"parent": slip.name},
            fields=["salary_component", "amount"]
        )
        for comp in components:
            key = comp.salary_component.lower().replace(" ", "_")
            row[key] = comp.amount
        data.append(row)
    return data
