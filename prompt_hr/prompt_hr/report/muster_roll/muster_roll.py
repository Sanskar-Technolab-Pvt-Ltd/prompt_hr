# Copyright (c) 2025, Jignasha Chavda and contributors
# For license information, please see license.txt

import frappe
import calendar
from frappe.utils import getdate, add_days, get_datetime

def execute(filters=None):
    columns = get_columns(filters)
    data = get_data(filters)
    message = get_header_html(filters)
    return columns, data, message

def get_header_html(filters):
    factory_name = "Prompt HR Pvt. Ltd."
    factory_address = "Plot No. 822/A/5, Krishna Ind. Estate, Nr. Kothari Cross Road, Santej, Kalol, Gandhinagar, Gujarat - 382721 (India)"
    month = frappe.utils.format_date(filters.get("from_date"), "MMM-yyyy") if filters else ""
    
    html = f"""
    <div style="margin-bottom: 20px;">
        <div style="font-weight: bold;">Form D</div>
        <div>(Prescribed under Rule 130)</div>
        <div style="font-weight: bold;">Muster Roll</div>
        <div><b>Name of Factory:</b> {factory_name}</div>
        <div><b>Place:</b> {factory_address}</div>
        <div><b>For the Month:</b> {filters.get("month")}</div>
    </div>
    """
    return html


def get_columns(filters):
    columns = [
        {"label": "Employee Name", "fieldname": "employee_name", "fieldtype": "Data", "width": 180},
        {"label": "Father's/Spouse's Name", "fieldname": "father_spouse_name", "fieldtype": "Data", "width": 180},
        {"label": "Date of Entry into Service", "fieldname": "date_of_joining", "fieldtype": "Date", "width": 120},
        {"label": "Nature of Work", "fieldname": "designation", "fieldtype": "Data", "width": 120},
    ]

    # Dynamic date columns for the selected month
    month = frappe.utils.getdate(filters.get("month")).month
    year = int(get_datetime().year)
    from_date = getdate(f"{year}-{month:02d}-01")
    last_day = calendar.monthrange(year, month)[1]
    to_date = getdate(f"{year}-{month:02d}-{last_day:02d}")
    day_count = (to_date - from_date).days + 1

    for i in range(day_count):
        day = add_days(from_date, i)
        columns.append({
            "label": day.strftime("%d %b %Y"),
            "fieldname": day.strftime("day_%d" % i),
            "fieldtype": "Data",
            "width": 60
        })

    return columns

def get_data(filters):
    # Dynamic date columns for the selected month
    month = frappe.utils.getdate(filters.get("month")).month
    year = int(get_datetime().year)
    from_date = getdate(f"{year}-{month:02d}-01")
    last_day = calendar.monthrange(year, month)[1]
    to_date = getdate(f"{year}-{month:02d}-{last_day:02d}")
    day_count = (to_date - from_date).days + 1


    employees = frappe.get_all(
        "Employee",
        fields=["name", "employee_name", "date_of_joining", "designation", "middle_name"],
        filters={"status": "Active"}
    )

    # Get attendance for the period
    attendance_map = {}
    attendance_records = frappe.get_all(
        "Attendance",
        fields=["employee", "attendance_date", "status", "leave_type"],
        filters={
            "attendance_date": ["between", [from_date, to_date]]
        }
    )
    for att in attendance_records:
        key = (att.employee, att.attendance_date)
        if att.status == "Present":
            attendance_map[key] = "P"
        elif att.status == "Absent":
            attendance_map[key] = "A"
        elif att.status == "On Leave":
            attendance_map[key] = "OL" if not att.leave_type else "".join(word[0] for word in att.leave_type.split(" ")).upper()
        elif att.status == "Half Day":
            attendance_map[key] = "HD"
        elif att.status == "Work From Home":
            attendance_map[key] = "WFH"
        else:
            attendance_map[key] = att.status[:2].upper()

    data = []
    for idx, emp in enumerate(employees, 1):
        row = {
            "sl_no": idx,
            "employee_name": emp.employee_name,
            "father_spouse_name": emp.middle_name or "",
            "date_of_joining": emp.date_of_joining,
            "designation": emp.designation,
        }
        # Fill attendance for each day
        day_count = (to_date - from_date).days + 1
        for i in range(day_count):
            day = add_days(from_date, i)
            key = (emp.name, day)
            row["day_%d" % i] = attendance_map.get(key, "")
        data.append(row)
    return data