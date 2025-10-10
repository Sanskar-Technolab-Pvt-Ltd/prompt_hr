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
        {"label": "Salary Slip ID", "fieldname":"salary_slip", "fieldtype":"Link", "options":"Salary Slip", "width":150},
        {"label": "Status", "fieldname":"status", "fieldtype":"Select", "width":150},
        {"label": "Type", "fieldname":"type", "fieldtype":"Data", "width":150},
        {"label": "Employee Number", "fieldname": "employee", "fieldtype": "Link", "options": "Employee", "width": 200},
        {"label": "Employee Name", "fieldname": "employee_name", "fieldtype": "Data", "width": 150},
        {"label": "Date Of Joining", "fieldname": "date_of_joining", "fieldtype": "Date", "width": 200},
        {"label": "Department", "fieldname": "department", "fieldtype": "Link", "options": "Department", "width": 120},
        {"label": "Designation", "fieldname": "designation", "fieldtype": "Data", "width": 120},
        {"label": "Employment Type", "fieldname": "worker_type", "fieldtype": "Data", "width": 200},
        {"label": "Gender", "fieldname": "gender", "fieldtype": "Data", "width": 90},
        {"label": "Date Of Birth", "fieldname": "date_of_birth", "fieldtype": "Date", "width": 110},
        {"label": "Location", "fieldname": "location", "fieldtype": "Data", "width": 120},
        {"label": "Cost Center", "fieldname": "cost_center", "fieldtype": "Link", "options": "Cost Center", "width": 120},
        # {"label": "Sub Department", "fieldname": "sub_department", "fieldtype": "Data", "width": 120},
        {"label": "Business Unit", "fieldname": "business_unit", "fieldtype": "Data", "width": 120},
        {"label": "Payroll Month", "fieldname": "payroll_month", "fieldtype": "Data", "width": 200},
        {"label": "PAN Number", "fieldname": "pan_number", "fieldtype": "Data", "width": 120},
        {"label": "UAN Number", "fieldname": "uan_number", "fieldtype": "Data", "width": 120},
        {"label":"Aadhaar Number", "fieldname":"aadhaar_number", "fieldtype":"Data", "width":200},
        # * WORKING DETAILS
        {"label": "Working Days", "fieldname": "working_days", "fieldtype": "Float", "width": 150},
        {"label": "Loss of Pay Days", "fieldname": "lop_days", "fieldtype": "Float", "width": 150},
        {"label": "Days Payable", "fieldname": "days_payable", "fieldtype": "Float", "width": 150},
        {"label": "LOP Reversal Days", "fieldname": "lop_reversal_days", "fieldtype": "Float", "width": 200},
        {"label": "Remuneration Amount", "fieldname": "remuneration_amount", "fieldtype": "Currency", "width": 200},
    ]

    #! GET SELECT FIELD OPTIONS FROM THE DOCTYPE
    custom_field_meta = frappe.get_meta("Salary Component").get_field("custom_salary_component_type")

    #? SAFELY GET OPTIONS AND SPLIT THEM INTO A LIST
    component_type_options = custom_field_meta.options.split("\n") if custom_field_meta and custom_field_meta.options else []


    earnings_columns = []
    deduction_columns = []

    found_other_earnings = False  #! FLAG TO CHECK IF "Other Earnings" TYPE IS SEEN
    for comp in component_type_options:
        comp_clean = (comp or "").strip()  #! REMOVE LEADING/TRAILING SPACES & HANDLE None
        calculated_width = max(120, len(comp) * 10 + 40)  # MIN WIDTH 120PX

        #! SKIP BLANKS AND "GRATUITY"
        if not comp_clean or comp_clean == "Gratuity":
            continue

        #? NORMALIZE FIELDNAME
        fieldname = comp.lower().replace(" ", "_")

        #! IF NOT YET FOUND "Other Earnings" TYPE → GO TO EARNINGS
        if not found_other_earnings:
            earnings_columns.append({
                "label": comp,
                "fieldname": fieldname,
                "fieldtype": "Currency",
                "width": calculated_width
            })

            #? FLIP FLAG IF "Other Earnings" FOUND
            if comp == "Other Earnings":
                found_other_earnings = True

        else:
            #! AFTER "Other Earnings" FOUND → ADD TO DEDUCTIONS
            deduction_columns.append({
                "label": comp,
                "fieldname": fieldname,
                "fieldtype": "Currency",
                "width": calculated_width
            })

    columns.extend(earnings_columns)  # * ADD EARNINGS
    columns.append({"label": "Gross Pay", "fieldname": "gross_pay", "fieldtype": "Currency", "width": 120})
    columns.extend(deduction_columns)  # * ADD DEDUCTIONS
    columns.append({"label": "Total Deductions", "fieldname": "total_deduction", "fieldtype": "Currency", "width": 200})
    columns.append({"label": "Salary Loan", "fieldname": "salary_loan", "fieldtype":"Currency", "width":200})
    columns.append({"label": "Net Pay", "fieldname": "net_pay", "fieldtype": "Currency", "width": 120})

    return columns

# ? FUNCTION TO FETCH DATA BASED ON FILTERS

def get_data(filters):
    # * DETERMINE FROM AND TO DATES FROM MONTH
    month = frappe.utils.getdate(filters.get("month")).month
    if filters.get("year"):
        year = int(filters.get("year"))
    else:
        year = int(get_datetime().year)
    from_date = getdate(f"{year}-{month}-01")
    last_day = calendar.monthrange(year, month)[1]
    to_date = getdate(f"{year}-{month}-{last_day}")

    # * FETCH SALARY SLIPS FOR GIVEN PERIOD
    salary_filters = {
        "start_date": from_date,
        "end_date": to_date,
    }

    # ? ADD OPTIONAL FILTERS IF PROVIDED
    if filters.get("company"):
        salary_filters["company"] = filters.get("company")

    if filters.get("department"):
        salary_filters["department"] = filters.get("department")

    if filters.get("designation"):
        salary_filters["designation"] = filters.get("designation")

    # ? STATUS → DEFAULT TO 'Submitted' IF NOT GIVEN
    status = filters.get("status", "Submitted")
    salary_filters["docstatus"] = 1 if status == "Submitted" else 0

    slips = frappe.get_all(
        "Salary Slip",
        filters=salary_filters,
        fields=["*"]
    )

    data = []
    employee_fnf = {}
    payroll_entries = set()

    # Collect payroll_entry references from slips
    for slip in slips:
        if slip.get("payroll_entry"):
            payroll_entries.add(slip["payroll_entry"])

    # Convert set to list and handle errors
    try:
        payroll_entries = list(payroll_entries)
    except Exception as e:
        frappe.log_error("Error converting payroll_entries to list", str(e))
        payroll_entries = []

    # Query Pending FnF Details if there are payroll entries
    child_table_data = []
    if payroll_entries:
        try:
            child_table_data = frappe.get_all(
                "Pending FnF Details",
                filters={
                    "parent": ["in", payroll_entries],
                    "parentfield": "custom_pending_fnf_details",
                    "parenttype": "Payroll Entry",
                    "fnf_record": ["is", "set"]
                },
                fields=["employee", "parent", "fnf_record"]
            )
        except Exception as e:
            frappe.log_error("Error fetching Pending FnF Details", str(e))
            child_table_data = []

    # Build the hash map: (employee, payroll_entry) => fnf_record
    for row in child_table_data:
        try:
            key = (row.get("employee"), row.get("parent"))
            employee_fnf[key] = row.get("fnf_record")
        except Exception as e:
            frappe.log_error("Error processing Pending FnF row", str(e))

    for slip in slips:

        employee = frappe.get_doc("Employee", slip.employee)

        # ? GET CUSTOM WORK LOCATION IF EXISTS
        work_location = ""
        type = "Salary"
        if employee.custom_work_location:
            work_location = frappe.db.get_value("Address", employee.custom_work_location, "address_title")

        # ? GET REMUNERATION FROM SALARY STRUCTURE ASSIGNMENT
        remuneration_amount = frappe.db.get_value("Salary Structure Assignment", slip.custom_salary_structure_assignment, "base") or 0
        # ? SET TYPE TO FNF IF FNF LINK TO PAYROLL AND FOR THAT EMPLOYEE
        if slip.payroll_entry:
            search_key = (slip.employee, slip.payroll_entry)
            try:
                if employee_fnf and employee_fnf.get(search_key):
                    type = "FnF"

            except:
                frappe.log_error("Error in Making key From Employee and Payroll Entry")

        # * BUILD ROW DATA
        row = {
            "salary_slip": slip.name,
            "status": slip.status,
            "type": type or "",
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
            "working_days": slip.total_working_days,
            "uan_number": employee.custom_uan_number,
            "aadhaar_number": employee.custom_aadhaar_number,
            "lop_days": slip.leave_without_pay,
            "days_payable": slip.payment_days,
            "lop_reversal_days": slip.custom_lop_days,
            "remuneration_amount": remuneration_amount,
            "gross_pay": slip.gross_pay,
            "total_deduction": slip.total_deduction,
            "net_pay": slip.net_pay,
            "salary_loan": slip.total_loan_repayment,
        }

        # * MAP SALARY COMPONENTS TO COLUMNS
        components = frappe.get_all(
            "Salary Detail",
            filters={"parent": slip.name},
            fields=["salary_component", "amount"]
        )

        for comp in components:
            salary_component_type = frappe.db.get_value("Salary Component", comp.salary_component, "custom_salary_component_type")

            if not salary_component_type:
                continue  #! SKIP IF FIELD IS EMPTY OR NULL

            key = salary_component_type.lower().replace(" ", "_")

            #! SAFELY INITIALIZE THE FIELD IF NOT PRESENT
            row[key] = row.get(key, 0) + comp.amount

        data.append(row)

    return data
