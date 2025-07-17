# Copyright (c) 2025, Jignasha Chavda and contributors
# For license information, please see license.txt

import frappe
from frappe.utils import get_first_day, get_last_day, get_datetime, getdate
import calendar

def execute(filters=None):
    columns = [
        {"label": "Employee Number", "fieldname": "employee", "fieldtype": "Link","options":"Employee", "width": 120},
        {"label": "Employee Name", "fieldname": "employee_name", "fieldtype": "Data", "width": 180},
        {"label": "PAN Number", "fieldname": "pan_number", "fieldtype": "Data", "width": 120},
        {"label": "Income Tax", "fieldname": "income_tax", "fieldtype": "Currency", "width": 100},
        {"label": "Surcharge", "fieldname": "surcharge", "fieldtype": "Currency", "width": 100},
        {"label": "Cess", "fieldname": "cess", "fieldtype": "Currency", "width": 100},
        {"label": "Total Tax Amount", "fieldname": "total_tax", "fieldtype": "Currency", "width": 120},
    ]

    data = []

    # Set the month and year from filters or default to current month
    month = frappe.utils.getdate(filters.get("month")).month
    year = int(get_datetime().year)
    from_date = getdate(f"{year}-{month}-01")
    last_day = calendar.monthrange(year, month)[1]
    to_date = getdate(f"{year}-{month}-{last_day}")

    if not month or not year:
        frappe.throw("Please select Month and Year in the report filters.")

    salary_slips = frappe.get_all(
        "Salary Slip",
        filters={
            "start_date": ["<=", from_date],
            "end_date": [">=", to_date],
            "docstatus": 1  # Only Submitted Salary Slips
        },
        fields=["name", "employee", "employee_name"]
    )

    for slip in salary_slips:
        # Fetch PAN Number from Employee if not in Salary Slip
        employee = frappe.get_doc("Employee", slip.employee)
        pan_number = frappe.db.get_value("Employee", slip.employee, "pan_number")

        salary_details = frappe.get_all(
            "Salary Detail",
            filters={"parent": slip.name},
            fields=["salary_component", "amount"],

        )
        income_tax = 0
        surcharge = 0
        cess = 0
        for detail in salary_details:
            salary_comp = frappe.get_doc("Salary Component", detail.salary_component)
            if salary_comp.custom_salary_component_type == "Income Tax":
                income_tax += detail.amount
            elif salary_comp.custom_salary_component_type == "Surcharge":
                surcharge += detail.amount
            elif salary_comp.custom_salary_component_type == "Cess":
                cess += detail.amount

        total_tax = income_tax + surcharge + cess
        data.append({
            "employee": employee.name,
            "employee_name": employee.employee_name,
            "pan_number": pan_number,
            "income_tax": income_tax,
            "surcharge": surcharge,
            "cess": cess,
            "total_tax": total_tax,
        })

    return columns, data
