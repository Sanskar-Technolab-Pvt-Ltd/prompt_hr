# Copyright (c) 2025, Jignasha Chavda and contributors
# For license information, please see license.txt

import frappe
import calendar
from datetime import datetime

def execute(filters=None):
    if not filters:
        filters = {}

    db_filters = {}

    # * GET MONTH FILTER
    month_str = filters.get("month")
    if month_str:
        try:
            # * Convert the month string to integer
            month = int(month_str)
            year = frappe.utils.getdate(frappe.utils.today()).year

            # * Set from_date to first day of month
            from_date = datetime(year, month, 1)

            # * Calculate last day of the month
            last_day = calendar.monthrange(year, month)[1]
            to_date = datetime(year, month, last_day)
        except Exception as e:
            # ! Invalid month input
            frappe.throw(f"Invalid month filter: {month_str}. Error: {str(e)}")
    else:
        # * Default to current month
        today = datetime.today()
        from_date = today.replace(day=1)
        last_day = calendar.monthrange(today.year, today.month)[1]
        to_date = today.replace(day=last_day)

    # ? Debug date range
    print(from_date, to_date)

    # * Apply employee filter if provided
    if filters.get("employee"):
        db_filters["employee"] = filters.get("employee")

    # * Filter by regularization date range
    if from_date and to_date:
        db_filters["regularization_date"] = ["between", [from_date.strftime("%Y-%m-%d"), to_date.strftime("%Y-%m-%d")]]

    # * Apply status filter if provided
    if filters.get("status"):
        db_filters["status"] = filters.get("status")

    # * Fetch filtered Attendance Regularization data
    data = frappe.get_all(
        "Attendance Regularization",
        filters=db_filters,
        fields=[
            "name",
            "employee",
            "employee_name",
            "regularization_date",
            "status"
        ],
        order_by="regularization_date DESC"
    )

    # * Define report columns
    columns = [
        {"label": "ID", "fieldname": "name", "fieldtype": "Link", "options": "Attendance Regularization", "width": 300},
        {"label": "Employee ID", "fieldname": "employee", "fieldtype": "Link", "options": "Employee", "width": 300},
        {"label": "Employee Name", "fieldname": "employee_name", "fieldtype": "Data", "width": 200},
        {"label": "Regularization Date", "fieldname": "regularization_date", "fieldtype": "Date", "width": 200},
        {"label": "Status", "fieldname": "status", "fieldtype": "Data", "width": 130},
    ]

    return columns, data
