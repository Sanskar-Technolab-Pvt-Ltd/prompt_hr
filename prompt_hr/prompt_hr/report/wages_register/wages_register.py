# Copyright (c) 2025, Jignasha Chavda and contributors
# For license information, please see license.txt

import frappe
from frappe.utils import getdate, get_datetime
import calendar

# ? EXECUTION ENTRY POINT
# ? RETURNS COLUMNS AND DATA BASED ON FILTERS

def execute(filters=None):
    columns = get_columns()  # ? GET ALL REQUIRED COLUMNS FOR THE REPORT
    data = get_data(filters)  # ? FETCH DATA BASED ON FILTERS
    return columns, data

# ? FUNCTION TO DEFINE COLUMN STRUCTURE

def get_columns():
    columns = [
        # * BASIC EMPLOYEE DETAILS
        {"label": "Employee Number", "fieldname": "employee", "fieldtype": "Link", "options": "Employee", "width": 120},
        {"label": "Employee Name", "fieldname": "employee_name", "fieldtype": "Data", "width": 150},
        {"label": "Job Title", "fieldname": "designation", "fieldtype": "Data", "width": 120},
        {"label": "Date Of Joining", "fieldname": "date_of_joining", "fieldtype": "Date", "width": 110},
        {"label": "Gender", "fieldname": "gender", "fieldtype": "Data", "width": 90},
        {"label": "Date Of Birth", "fieldname": "date_of_birth", "fieldtype": "Date", "width": 110},
        {"label": "Location", "fieldname": "location", "fieldtype": "Data", "width": 120},
        {"label": "Department", "fieldname": "department", "fieldtype": "Link", "options": "Department", "width": 120},
        {"label": "Sub Department", "fieldname": "sub_department", "fieldtype": "Data", "width": 120},
        {"label": "Worker Type", "fieldname": "worker_type", "fieldtype": "Data", "width": 110},
        {"label": "Cost Center", "fieldname": "cost_center", "fieldtype": "Link", "options": "Cost Center", "width": 120},
        {"label": "Business Unit", "fieldname": "business_unit", "fieldtype": "Data", "width": 120},
        {"label": "PAN Number", "fieldname": "pan_number", "fieldtype": "Data", "width": 120},
        {"label": "Payroll Month", "fieldname": "payroll_month", "fieldtype": "Data", "width": 100},
        {"label": "Status", "fieldname": "status", "fieldtype": "Data", "width": 100},
        # * WORKING DETAILS
        {"label": "Working Days", "fieldname": "working_days", "fieldtype": "Float", "width": 100},
        {"label": "Loss of Pay Days", "fieldname": "lop_days", "fieldtype": "Float", "width": 100},
        {"label": "Days Payable", "fieldname": "days_payable", "fieldtype": "Float", "width": 100},
        {"label": "LOP Reversal Days", "fieldname": "lop_reversal_days", "fieldtype": "Float", "width": 100},
        {"label": "Remuneration Amount", "fieldname": "remuneration_amount", "fieldtype": "Currency", "width": 150},
    ]

    # ? ADD DYNAMIC EARNING AND DEDUCTION COMPONENTS
    dynamic_components = frappe.get_all(
        "Salary Component",
        filters={"disabled": 0},
        fields=["name", "type"]
    )

    earnings_columns = []
    deduction_columns = []

    for comp in dynamic_components:
        if comp.type == "Earning":
            earnings_columns.append({
                "label": comp.name,
                "fieldname": comp.name.lower().replace(" ", "_"),
                "fieldtype": "Currency",
                "width": 120
            })
        elif comp.type == "Deduction":
            deduction_columns.append({
                "label": comp.name,
                "fieldname": comp.name.lower().replace(" ", "_"),
                "fieldtype": "Currency",
                "width": 120
            })

    columns.extend(earnings_columns)  # * ADD EARNINGS
    columns.append({"label": "Gross(A)", "fieldname": "gross_pay", "fieldtype": "Currency", "width": 120})
    columns.extend(deduction_columns)  # * ADD DEDUCTIONS
    columns.append({"label": "Total Deductions", "fieldname": "total_deduction", "fieldtype": "Currency", "width": 120})
    columns.append({"label": "Net Pay", "fieldname": "net_pay", "fieldtype": "Currency", "width": 120})
    columns.append({"label": "Salary Loan", "fieldname": "salary_loan", "fieldtype":"Currency", "width":200})

    return columns

# ? FUNCTION TO FETCH DATA BASED ON FILTERS

def get_data(filters):
    # * DETERMINE FROM AND TO DATES FROM MONTH
    month = frappe.utils.getdate(filters.get("month")).month
    year = int(get_datetime().year)
    from_date = getdate(f"{year}-{month}-01")
    last_day = calendar.monthrange(year, month)[1]
    to_date = getdate(f"{year}-{month}-{last_day}")

    # * FETCH SALARY SLIPS FOR GIVEN PERIOD
    slips = frappe.get_all(
        "Salary Slip",
        filters={"start_date": from_date, "end_date":to_date, "docstatus":1},
        fields=["*"]
    )

    data = []
    for slip in slips:

        employee = frappe.get_doc("Employee", slip.employee)

        # ? GET CUSTOM WORK LOCATION IF EXISTS
        if employee.custom_work_location:
            work_location = frappe.db.get_value("Address", employee.custom_work_location, "address_title")

        # ? GET REMUNERATION FROM SALARY STRUCTURE ASSIGNMENT
        remuneration_amount = 0
        if slip.salary_structure:
            salary_structure_assignment = frappe.get_all(
                "Salary Structure Assignment",
                filters={"employee":slip.employee, "salary_structure":slip.salary_structure, "docstatus":1, "from_date": ["<=", slip.from_date]},
                fields=["name", "base"],
                order_by= "from_date desc",
                limit=1
            )
            remuneration_amount = salary_structure_assignment[0].base

        # * BUILD ROW DATA
        row = {
            "employee": slip.employee,
            "employee_name": slip.employee_name,
            "designation": employee.designation,
            "date_of_joining": employee.date_of_joining,
            "gender": employee.gender,
            "date_of_birth": employee.date_of_birth,
            "location": work_location,
            "department": employee.department,
            "sub_department": employee.custom_subdepartment,
            "worker_type": employee.employment_type,
            "cost_center": employee.payroll_cost_center,
            "business_unit": employee.custom_business_unit,
            "pan_number": frappe.get_value("Employee", slip.employee, "pan_number"),
            "payroll_month": filters.get("month"),
            "status": slip.status,
            "working_days": slip.total_working_days,
            "lop_days": slip.leave_without_pay,
            "days_payable": slip.payment_days,
            "lop_reversal_days": slip.custom_lop_days,
            "remuneration_amount": remuneration_amount,
            "gross_pay": slip.gross_pay,
            "total_deduction": slip.total_deduction,
            "net_pay": slip.net_pay,
            "salary_loan": slip.total_loan_repayment
        }

        # * MAP SALARY COMPONENTS TO COLUMNS
        components = frappe.get_all(
            "Salary Detail",
            filters={"parent": slip.name},
            fields=["salary_component", "amount"]
        )

        for comp in components:
            key = comp.salary_component.lower().replace(" ", "_")
            row[key] = comp.amount

        data.append(row)  # > ADD ROW TO FINAL DATA

    return data
