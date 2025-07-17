# Copyright (c) 2025, Jignasha Chavda and contributors
# For license information, please see license.txt

import frappe
from frappe.utils import getdate, get_datetime
import calendar

def execute(filters=None):
    if not filters or not filters.get("month"):
        frappe.throw("Please provide both Month and Year filters to run the report.")

    month = frappe.utils.getdate(filters.get("month")).month
    year = int(get_datetime().year)
    # Define the report columns
    columns = [
        {"label": "Employee Number", "fieldname": "employee", "fieldtype": "Link","options":"Employee", "width": 150},
        {"label": "Employee Name", "fieldname": "employee_name", "fieldtype": "Data", "width": 200},
        {"label": "State", "fieldname": "state", "fieldtype": "Data", "width": 120},
        {"label": "Registered Location", "fieldname": "registered_location", "fieldtype": "Data", "width": 180},
        {"label": "Gross Amount", "fieldname": "gross_amount", "fieldtype": "Currency", "width": 120},
        {"label": "Tax Amount", "fieldname": "tax_amount", "fieldtype": "Currency", "width": 120},
    ]

    # Set the start and end date for the selected month
    from_date = getdate(f"{year}-{month:02d}-01")
    last_day = calendar.monthrange(year, month)[1]
    to_date = getdate(f"{year}-{month:02d}-{last_day}")

    # Filters for Salary Slips
    salary_slip_filters = {
        "docstatus": 1,
        "start_date": from_date,
        "end_date": to_date
    }

    # Fetch Salary Slips
    salary_slips = frappe.get_all(
        "Salary Slip",
        fields=["employee", "employee_name", "gross_pay", "name"],
        filters=salary_slip_filters
    )

    data = []
    for slip in salary_slips:
        employee = frappe.get_doc("Employee", slip.employee)
        salary_details = frappe.get_all(
            "Salary Detail",
            filters={"parent": slip.name},
            fields=["salary_component", "amount"],

        )
        tax = 0
        for detail in salary_details:
            salary_comp = frappe.get_doc("Salary Component", detail.salary_component)
            print(salary_comp)
            if salary_comp.custom_salary_component_type == "Professional Tax":
                tax += detail.amount
        work_location = frappe.db.get_value("Employee", employee.name, "custom_work_location")
        work_location_name = frappe.db.get_value("Address", work_location, "address_title") if work_location else "N/A"
        row = {
            "employee": employee.name,
            "employee_name": slip.employee_name,
            "state": employee.get("custom_permanent_state"),
            "registered_location":work_location_name,
            "gross_amount": slip.gross_pay or 0.0,
            "tax_amount": tax
        }
        data.append(row)

    message = f"<h3>Prompt Equipments Pvt. Ltd.</h3><h4>Professional Tax Summary - {calendar.month_name[month]} {year}</h4>"

    return columns, data, message
