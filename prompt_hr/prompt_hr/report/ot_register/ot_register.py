# Copyright (c) 2025, Jignasha Chavda and contributors
# For license information, please see license.txt

import frappe
from frappe.utils import get_first_day, get_last_day, formatdate
from datetime import datetime

def execute(filters=None):
    columns = get_columns()
    data = []

    company = filters.get("company")
    month = filters.get("month")
    from_date = get_first_day(month)
    to_date = get_last_day(month)

    # Fetch Company Name and Address
    company_doc = frappe.get_doc("Company", company)

    # Fetch the primary address linked to the company
    address_name = frappe.get_all("Dynamic Link", {
        "link_doctype": "Company",
        "link_name": company,
        "parenttype": "Address",
    }, "parent")

    address_display = "Not Found"
    if address_name:
        address_doc = frappe.get_doc("Address", address_name[0].parent)
        address_display = ", ".join([
        address_doc.address_line1 or "",
        address_doc.address_line2 or "",
        address_doc.city or "",
        address_doc.county or "",
        address_doc.state or "",
        address_doc.country or "",
        str(address_doc.pincode) or ""]
        )

    # Header
    header_message = [
        f"<b>Name and Address of Principal Employer :\t\tSHREYAS MEHTA, 11, SWI PARK SOCIETY, NEAR MANARAV HALL, RANNA PARK, GHATLODIA, , AHMEDABAD Gujarat, IN 380061</b><br>",
        f"<b>Name and Address of Establishment :\t\t{company_doc.name}, {address_display}</b><br>",
        f"<b>For the Month of:\t\t{formatdate(from_date, 'MMM-YYYY')}</b>"
    ]
    # Threshold
    threshold_hours = frappe.db.get_single_value("HR Settings", "standard_working_hours") or 8
    overtime_multiplier = 2.0

    # Fetch all attendance records where overtime is possible
    attendance_records = frappe.get_all("Attendance",
        fields=["name", "employee", "employee_name", "attendance_date", "in_time", "out_time", "working_hours"],
        filters={"docstatus": 1, "status": "Present", "company": company, "attendance_date": ["between", [from_date, to_date]]},
        order_by="employee_name, attendance_date"
    )

    employee_map = {}

    for att in attendance_records:
        # Get in_time/out_time or use defaults
        # in_time = att.in_time or datetime.combine(att.attendance_date, datetime.strptime("09:00", "%H:%M").time())
        # out_time = att.out_time or datetime.combine(att.attendance_date, datetime.strptime("18:00", "%H:%M").time())

        # Convert if str
        # if isinstance(in_time, str): in_time = datetime.strptime(in_time, "%Y-%m-%d %H:%M:%S")
        # if isinstance(out_time, str): out_time = datetime.strptime(out_time, "%Y-%m-%d %H:%M:%S")
        worked_hours = att.working_hours or 0
        if att.in_time and att.out_time and worked_hours == 0:
            worked_hours = att.working_hours or round((att.out_time - att.in_time).total_seconds() / 3600, 2)
        overtime_hours = max(0, worked_hours - threshold_hours)

        if overtime_hours > 0:
            emp = frappe.get_doc("Employee", att.employee)
            emp_data = employee_map.get(att.employee, {
                "employee": att.employee,
                "employee_name": att.employee_name,
                "father_name": getattr(emp, "middle_name", "") or "-",
                "gender": emp.gender or "-",
                "designation": emp.designation or "Unknown",
                "ot_dates": [],
                "total_ot_hours": 0,
            })

            emp_data["ot_dates"].append(att.attendance_date.strftime("%d %b %Y"))
            emp_data["total_ot_hours"] += overtime_hours

            employee_map[att.employee] = emp_data

    # Final row assembly
    for emp_id, row in employee_map.items():
        # Calculate wages
        standard_working_days = 26 # Assuming 26 working days in a month
        normal_rate = frappe.db.get_value("Employee",emp_id, "custom_gross_salary")/threshold_hours/standard_working_days
        ot_hourly_rate = (normal_rate ) * overtime_multiplier
        ot_earnings = round(row["total_ot_hours"] * ot_hourly_rate)

        data.append([
            row["employee_name"],
            row["father_name"],
            row["gender"],
            row["designation"],
            ", ".join(row["ot_dates"]),
            f"{int(row['total_ot_hours'])}:{int((row['total_ot_hours'] % 1) * 60):02}",
            normal_rate,
            ot_hourly_rate,
            ot_earnings,
            frappe.utils.today(),
            ""
        ])

    return columns, data, header_message

def get_columns():
    return [
        {"label": "Name of the Employee", "fieldname": "employee_name", "fieldtype": "Data", "width": 180},
        {"label": "Father's/Husband's Name", "fieldname": "father_name", "fieldtype": "Data", "width": 160},
        {"label": "Sex", "fieldname": "gender", "fieldtype": "Data", "width": 80},
        {"label": "Designation / Nature of Employment", "fieldname": "designation", "fieldtype": "Data", "width": 200},
        {"label": "Dates on which overtime worked", "fieldname": "ot_dates", "fieldtype": "Data", "width": 250},
        {"label": "Total Overtime worked or Production in case of piece rate", "fieldname": "total_ot", "fieldtype": "Data", "width": 130},
        {"label": "Normal Rate of Wages", "fieldname": "normal_rate", "fieldtype": "Currency", "width": 130},
        {"label": "Overtime Rate of Wages", "fieldname": "ot_rate", "fieldtype": "Currency", "width": 150},
        {"label": "Overtime Earnings", "fieldname": "ot_earnings", "fieldtype": "Currency", "width": 140},
        {"label": "Date on which overtime wages paid", "fieldname": "paid_date", "fieldtype": "Date", "width": 120},
        {"label": "Remarks", "fieldname": "remarks", "fieldtype": "Data", "width": 120}
    ]
