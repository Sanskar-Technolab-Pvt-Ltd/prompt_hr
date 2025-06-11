# Copyright (c) 2025, Jignasha Chavda and contributors
# For license information, please see license.txt

import frappe
from frappe.utils import getdate, get_datetime
import calendar

def execute(filters=None):
    columns = [
        {"label": "Empno.", "fieldtype": "Data", "fieldname": "employee_number", "width": 100},
        {"label": "Name", "fieldtype": "Data", "fieldname": "employee_name", "width": 180},
        {"label": "Department", "fieldtype": "Data", "fieldname": "department", "width": 120},
        {"label": "Payment Mode", "fieldtype": "Data", "fieldname": "payment_mode", "width": 120},
        {"label": "Bank", "fieldtype": "Data", "fieldname": "bank_name", "width": 120},
        {"label": "IFSC Code", "fieldtype": "Data", "fieldname": "ifsc_code", "width": 120},
        {"label": "Bank Account No", "fieldtype": "Data", "fieldname": "bank_account_no", "width": 140},
        {"label": "Payment For", "fieldtype": "Data", "fieldname": "payment_for", "width": 100},
        {"label": "Amount", "fieldtype": "Currency", "fieldname": "amount", "width": 100},
    ]

    data = []
    month = frappe.utils.getdate(filters.get("month")).month
    year = int(get_datetime().year)
    from_date = getdate(f"{year}-{month:02d}-01")
    last_day = calendar.monthrange(year, month)[1]
    to_date = getdate(f"{year}-{month:02d}-{last_day}")
    # Fetch Salary Slips for the selected month and year
    salary_slips = frappe.get_all(
        "Salary Slip",
        filters={
            "start_date": from_date,
            "end_date": to_date,
            "docstatus": 1  # Only submitted
        },
        fields=[
            "name", "employee", "employee_name", "department",
            "mode_of_payment", "bank_name", "bank_account_no", "net_pay"
        ]
    )

    for slip in salary_slips:
        employee = frappe.get_doc("Employee", slip.employee)
        data.append({
            "employee": employee.employee_number,
            "employee_name": employee.employee_name,
            "department": employee.department,
            "payment_mode": slip.mode_of_payment,
            "bank_name": slip.bank_name,
            "ifsc_code": "NA",
            "bank_account_no": slip.bank_account_no,
            "payment_for": "Salary",
            "amount": slip.net_pay,
        })

    # Message to display on the report
    message = f"Bank Transfer Statement for the month of {month}, {year} (Currency: INR)"

    return columns, data, None, message
