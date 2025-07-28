# Copyright (c) 2025, Jignasha Chavda and contributors
# For license information, please see license.txt

import frappe
from frappe.utils import getdate, add_months, format_date
import calendar

def execute(filters=None):
    columns = [
        {"label": "Employee No.", "fieldtype": "Link", "fieldname": "employee","options":'Employee', "width": 160},
        {"label": "Name", "fieldtype": "Data", "fieldname": "employee_name", "width": 180},
        {"label": "Department", "fieldtype": "Data", "fieldname": "department", "width": 160},
        {"label": "Payment Mode", "fieldtype": "Data", "fieldname": "payment_mode", "width": 160},
        {"label": "Bank", "fieldtype": "Data", "fieldname": "bank_name", "width": 160},
        {"label": "IFSC Code", "fieldtype": "Data", "fieldname": "ifsc_code", "width": 160},
        {"label": "Bank Account No", "fieldtype": "Data", "fieldname": "bank_account_no", "width": 200},
        {"label": "Payment For", "fieldtype": "Data", "fieldname": "payment_for", "width": 160},
        {"label": "Amount", "fieldtype": "Currency", "fieldname": "amount", "width": 200},
    ]

    data = []
    from_date = filters.get("from_date") or getdate()
    to_date = filters.get("to_date") or add_months(from_date, 1)

    # ? MAKE SALARY SLIP FILTERS
    salary_slip_filters = {
        "start_date": from_date,
        "end_date": to_date,
        "docstatus": 1
    }
    if filters.get("company"):
        salary_slip_filters.update({"company": filters.get("company")})

    salary_slips = frappe.get_all(
        "Salary Slip",
        filters= salary_slip_filters,
        fields=[
            "name", "employee", "employee_name", "department",
            "mode_of_payment", "bank_name", "bank_account_no", "net_pay"
        ]
    )

    for slip in salary_slips:
        employee = frappe.get_doc("Employee", slip.employee)
        if employee.salary_mode == "Bank":
            data.append({
                "employee": slip.employee,
                "employee_name": slip.employee_name,
                "department": slip.department,
                "payment_mode": 'Bank Transfer',
                "bank_name": employee.bank_name,
                "ifsc_code": employee.ifsc_code,
                "bank_account_no": employee.bank_ac_no,
                "payment_for": "Salary",
                "amount": slip.net_pay,
            })

    # Message to display on the report
    message = f"<h3>Bank Transfer Statement from the date {format_date(from_date, 'dd-MM-yyyy')} to {format_date(to_date, 'dd-MM-yyyy')} (Currency: INR)</h3>"

    return columns, data, message
