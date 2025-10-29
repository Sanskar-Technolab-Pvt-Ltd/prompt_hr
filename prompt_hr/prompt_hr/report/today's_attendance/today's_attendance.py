# Copyright (c) 2025, Jignasha Chavda and contributors
# For license information, please see license.txt

import frappe
from frappe.utils import today, getdate

def execute(filters=None):
    if not filters:
        filters = {}

    date = filters.get("date") or today()
    employee = filters.get("employee")
    department = filters.get("department")
    work_location = filters.get("work_location")

    #? DEFINE REPORT COLUMNS
    columns = [
        {"label": "Employee Code", "fieldname": "employee", "fieldtype": "Link", "options": "Employee", "width": 120},
        {"label": "Employee Name", "fieldname": "employee_name", "fieldtype": "Data", "width": 160},
        {"label": "Department", "fieldname": "department", "fieldtype": "Link", "options": "Department", "width": 140},
        {"label": "Work Location", "fieldname": "work_location", "fieldtype": "Link", "options": "Address", "width": 140},
        {"label": "Date", "fieldname": "date", "fieldtype": "Date", "width": 110},
        {"label": "Status", "fieldname": "status", "fieldtype": "Data", "width": 400},
    ]

    #? BUILD FILTERS FOR EMPLOYEE FETCH
    emp_filters = {}
    if employee:
        emp_filters["name"] = employee
    if department:
        emp_filters["department"] = department
    if work_location:
        emp_filters["custom_work_location"] = work_location

    or_filters = [{"relieving_date": [">=", date]}, {"relieving_date": ["is", "not set"]}]
    employees = frappe.get_all(
        "Employee",
        filters=emp_filters,
        or_filters=or_filters,
        fields=["name", "employee_name", "department", "custom_work_location"]
    )

    #? GET ALL EMPLOYEE NAMES
    employee_list = [emp.name for emp in employees]
    if not employee_list:
        return columns, []

    #? PRECOMPUTE STATUSES IN BULK
    employee_status_map = get_all_employee_statuses(employee_list, date)

    #? BUILD FINAL DATA
    data = []
    for emp in employees:
        emp_status = employee_status_map.get(emp.name, "")
        data.append({
            "employee": emp.name,
            "employee_name": emp.employee_name,
            "department": emp.department,
            "work_location": emp.custom_work_location,
            "date": date,
            "status": emp_status
        })

    return columns, data


def get_all_employee_statuses(employee_list, date):
    """
    #! FETCH AND PREPARE EMPLOYEE STATUS FOR ALL EMPLOYEES AT ONCE
    """
    status_map = {emp: [] for emp in employee_list}

    #? 1️⃣ FETCH LEAVES
    leaves = frappe.get_all(
        "Leave Application",
        filters={
            "employee": ["in", employee_list],
            "from_date": ["<=", date],
            "to_date": [">=", date],
            "workflow_state": ["not in", ["Rejected", "Cancelled"]],
        },
        fields=["employee", "half_day", "half_day_date", "custom_half_day_time"],
    )

    for leave in leaves:
        if leave.half_day and getdate(leave.half_day_date) == getdate(date):
            status_map[leave.employee].append(f"On Leave (HD-{leave.custom_half_day_time})")
        else:
            status_map[leave.employee].append("On Leave")

    #? 2️⃣ FETCH ATTENDANCE REQUESTS
    attendance_requests = frappe.get_all(
        "Attendance Request",
        filters={
            "employee": ["in", employee_list],
            "from_date": ["<=", date],
            "to_date": [">=", date],
            "workflow_state": ["not in", ["Rejected", "Cancelled"]],
        },
        fields=["employee", "reason"],
    )

    for req in attendance_requests:
        reason = req.reason
        if reason == "Work From Home":
            status_map[req.employee].append("WFH")
        elif reason in ["On Duty", "Partial Day"]:
            status_map[req.employee].append(reason)

    #? 3️⃣ FETCH CHECKINS
    checkins = frappe.get_all(
        "Employee Checkin",
        filters={
            "employee": ["in", employee_list],
            "time": ["between", [f"{date} 00:00:00", f"{date} 23:59:59"]],
            "log_type": "IN",
        },
        fields=["employee"],
    )

    for checkin in checkins:
        status_map[checkin.employee].append("Present")

    #? 4️⃣ COMBINE STATUSES
    combined_map = {emp: ", ".join(set(status_list)) for emp, status_list in status_map.items() if status_list}

    return combined_map
