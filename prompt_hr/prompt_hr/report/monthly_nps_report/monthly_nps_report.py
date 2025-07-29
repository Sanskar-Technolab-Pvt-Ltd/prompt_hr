# Copyright (c) 2025, Jignasha Chavda and contributors
# For license information, please see license.txt

import frappe
from frappe.utils import getdate, format_date

def execute(filters=None):
	columns, data = get_columns(filters), get_data(filters)
	return columns, data

def get_columns(filters):
	return [
    {
        "label": "Emp Code",
        "fieldname": "employee",
        "fieldtype": "Link",
        "options": "Employee",
        "width": 150,
    },
    {
        "label": "PRAN No",
        "fieldname": "pran_no",
        "fieldtype": "Data",
        "width": 150,
    },
    {
        "label": "Date_of_Birth_DD_MMM_YYYY",
        "fieldname": "dob",
        "fieldtype": "Data",
        "width": 250,
    },
    {
        "label": "Tier_Flag",
        "fieldname": "tier_flag",
        "fieldtype": "Int",
        "width": 150,
    },
    {
        "label": "Employer_contribution",
        "fieldname": "employer_contribution",
        "fieldtype": "Currency",
        "width": 200,
    },
    {
        "label": "Subscriber_contribution",
        "fieldname": "subscriber_contribution",
        "fieldtype": "Currency",
        "width": 200,
    },
    {
        "label": "Gross_Contribution_Amount",
        "fieldname": "gross_contribution_amount",
        "fieldtype": "Currency",
        "width": 250,
    },
    {
        "label": "Remarks",
        "fieldname": "remarks",
        "fieldtype": "Data",
        "width": 200,
    },
    {
        "label": "Month",
        "fieldname": "month",
        "fieldtype": "Int",
        "width": 100,
    },
    {
        "label": "Year",
        "fieldname": "year",
        "fieldtype": "Int",
        "width": 100,
    },
]


def get_data(filters):
	# Set the start and end date for the selected month
    from_date = getdate(filters.get("from_date"))
    to_date = getdate(filters.get("to_date"))

    # Filters for Salary Slips
    salary_slip_filters = {
        "docstatus": 1,
        "start_date": from_date,
        "end_date": to_date
    }

    if filters.get("company"):
        salary_slip_filters.update({"company": filters.get("company")})

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
            filters={"parent": slip.name, "parentfield":"deductions"},
            fields=["salary_component", "amount"],

        )
        nps_contribution = 0
        for detail in salary_details:
            salary_comp = frappe.get_doc("Salary Component", detail.salary_component)
            if salary_comp.custom_salary_component_type == "NPS Contribution":
                nps_contribution += detail.amount

        if employee.custom_nps_consent == 1 and employee.status=="Active":
            row = {
                "employee": slip.employee,
                "pran_no": employee.custom_pran_number,
                "dob": format_date(employee.date_of_birth, "dd-MMM-yyyy"),
                "tier_flag":1,
                "employer_contribution": nps_contribution,
                "subscriber_contribution": 0,
                "gross_contribution_amount": nps_contribution,
                "remarks": slip.employee_name,
                "month": from_date.month,
                "year": from_date.year,
            }
            data.append(row)

    return data
