# Copyright (c) 2025, Jignasha Chavda and contributors
# For license information, please see license.txt

import frappe
from frappe.utils import getdate, add_months
import calendar

def execute(filters=None):
    columns = [
        {"label": "Employee Number", "fieldname": "employee", "fieldtype": "Link","options":"Employee", "width": 200},
        {"label": "Employee Name", "fieldname": "employee_name", "fieldtype": "Data", "width": 180},
        {"label": "PAN Number", "fieldname": "pan_number", "fieldtype": "Data", "width": 150},
        {"label": "Income Tax", "fieldname": "income_tax", "fieldtype": "Currency", "width": 150},
        {"label": "Surcharge", "fieldname": "surcharge", "fieldtype": "Currency", "width": 150},
        {"label": "Cess", "fieldname": "cess", "fieldtype": "Currency", "width": 150},
        {"label": "Total Tax Amount", "fieldname": "total_tax", "fieldtype": "Currency", "width": 200},
    ]

    data = []

    # Set the month and year from filters or default to current month
    from_date = filters.get("from_date") or getdate()
    to_date = filters.get("to_date") or add_months(from_date, 1)

    # ? MAKE SALARY SLIP FILTERS
    salary_slip_filters = {
        "start_date": ["<=", from_date],
        "end_date": [">=", to_date],
        "docstatus": 1
    }
    if filters.get("company"):
        salary_slip_filters.update({"company": filters.get("company")})
    
    salary_slips = frappe.get_all(
        "Salary Slip",
        filters= salary_slip_filters,
        fields=["name", "employee", "employee_name"]
    )

    for slip in salary_slips:
        # Fetch PAN Number from Employee if not in Salary Slip
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
            elif salary_comp.custom_salary_component_type == "Education Cess":
                cess += detail.amount

        total_tax = income_tax + surcharge + cess
        if income_tax > 0:
            data.append({
                "employee": slip.employee,
                "employee_name": slip.employee_name,
                "pan_number": pan_number,
                "income_tax": income_tax,
                "surcharge": surcharge,
                "cess": cess,
                "total_tax": total_tax,
            })

    return columns, data
