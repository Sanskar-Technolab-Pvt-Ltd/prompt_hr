# Copyright (c) 2025, Jignasha Chavda and contributors
# For license information, please see license.txt

import frappe
from datetime import datetime
import calendar

def execute(filters=None):
    if not filters:
        filters = {}

    # * GET MONTH
    month_str = filters.get("month")
    db_filters = {}

    if month_str:
        try:
            month = int(month_str)
            year = frappe.utils.getdate(frappe.utils.today()).year
            from_date = datetime(year, month, 1)
            last_day = calendar.monthrange(year, month)[1]
            to_date = datetime(year, month, last_day)
        except Exception as e:
            frappe.throw(f"Invalid month filter: {month_str}. Error: {str(e)}")
    else:
        today = datetime.today()
        from_date = today.replace(day=1)
        last_day = calendar.monthrange(today.year, today.month)[1]
        to_date = today.replace(day=last_day)

    db_filters["from_date"] = ["<=", to_date.strftime("%Y-%m-%d")]
    db_filters["to_date"] = [">=", from_date.strftime("%Y-%m-%d")]

    if filters.get("employee"):
        db_filters["employee"] = filters["employee"]

    if filters.get("workflow_state"):
        db_filters["workflow_state"] = filters["workflow_state"]
        if filters.get("workflow_state") == "Pending":
            db_filters["status"] = "Open"
        else:
            db_filters["status"] = filters.get("workflow_state")

    data = frappe.get_all(
        "Leave Application",
        filters=db_filters,
        fields=[
            "name",
            "employee",
            "employee_name",
            "from_date",
            "to_date",
            "total_leave_days",
            "leave_type",
            "workflow_state",
        ],
        order_by="from_date DESC"
    )

    columns = [
        {"label": "ID", "fieldname": "name", "fieldtype": "Data", "width": 300},
        {"label": "Employee ID", "fieldname": "employee", "fieldtype": "Link", "options": "Employee", "width": 300},
        {"label": "Employee Name", "fieldname": "employee_name", "fieldtype": "Data", "width": 200},
        {"label": "From Date", "fieldname": "from_date", "fieldtype": "Date", "width": 150},
        {"label": "To Date", "fieldname": "to_date", "fieldtype": "Date", "width": 150},
        {"label": "Total Leave Days", "fieldname": "total_leave_days", "fieldtype": "Float", "width": 200},
        {"label": "Leave Type", "fieldname": "leave_type", "fieldtype": "Link", "options": "Leave Type", "width": 200},
        {"label": "Workflow State", "fieldname": "workflow_state", "fieldtype": "Data", "width": 170},
    ]

    return columns, data
