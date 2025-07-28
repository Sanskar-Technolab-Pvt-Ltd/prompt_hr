# Copyright (c) 2025, Jignasha Chavda and contributors
# For license information, please see license.txt

import frappe
from frappe.utils import getdate, add_months
import calendar

def execute(filters=None):
    # Set the month and year from filters or default to current month
    from_date = filters.get("from_date") or getdate()
    to_date = filters.get("to_date") or add_months(from_date, 1)

    columns = [
        {"label": "UAN", "fieldname": "employee_number", "fieldtype": "Data", "width": 120},
        {"label": "MEMBER NAME", "fieldname": "employee_name", "fieldtype": "Data", "width": 180},
        {"label": "GROSS WAGES", "fieldname": "gross_wages", "fieldtype": "Currency", "width": 200},
        {"label": "EPF WAGES", "fieldname": "epf_wages", "fieldtype": "Currency", "width": 200},
        {"label": "EPS WAGES", "fieldname": "eps_wages", "fieldtype": "Currency", "width": 200},
        {"label": "EDLI WAGES", "fieldname": "edli_wages", "fieldtype": "Currency", "width": 200},
        {"label": "EE SHARE REMITTED", "fieldname": "ee_share_remitted", "fieldtype": "Currency", "width": 200},
        {"label": "EPS CONTRIBUTION REMITTED", "fieldname": "eps_contribution_remitted", "fieldtype": "Currency", "width": 200},
        {"label": "ER SHARE REMITTED", "fieldname": "er_share_remitted", "fieldtype": "Currency", "width": 200},
        {"label": "NCP DAYS", "fieldname": "ncp_days", "fieldtype": "Int", "width": 120},
        {"label": "REFUNDS", "fieldname": "refund_of_advance", "fieldtype": "Data", "editable":1, "width": 150},
    ]


    # Fetch Employee Name and Number from Salary Slip
    data = []
    filters.setdefault("docstatus", 1)

    # Base filters
    salary_filters = {
        "start_date": from_date,
        "end_date": to_date,
        "docstatus": 1
    }

    # Add employee filter only if present
    if filters.get("company"):
        salary_filters["company"] = filters.get("company")

    salary_slips = frappe.get_all(
        "Salary Slip",
        fields=["employee", "employee_name", "gross_pay", "name", "leave_without_pay"],
        filters=salary_filters
    )

    for slip in salary_slips:
        employee = frappe.get_doc("Employee", slip.employee)
        salary_details = frappe.get_all(
            "Salary Detail",
            filters={"parent": slip.name},
            fields=["salary_component", "amount", "parentfield"],

        )
        basic = 0
        dearness_allowance = 0
        provident_fund = 0
        if salary_details:
            for salary_detail in salary_details:
                salary_comp = frappe.get_doc("Salary Component", salary_detail.salary_component)
                if salary_comp.custom_salary_component_type == "Basic Salary":
                    basic += salary_detail.amount
                elif salary_comp.custom_salary_component_type == "Dearness Allowance":
                    dearness_allowance += salary_detail.amount
                elif salary_comp.custom_salary_component_type == "PF Employee Contribution" and salary_detail.parentfield=="deductions":
                    provident_fund += salary_detail.amount
        
        epf_wages = basic + dearness_allowance
        if epf_wages > 15000:
            eps_wages = 15000
        else:
            eps_wages = epf_wages
        ee_share_remitted = epf_wages * 0.12
        eps_contribution_remitted = eps_wages * 0.0833
        if provident_fund > 0:
            row = {
                "employee_number": employee.custom_uan_number,
                "employee_name": slip.employee_name,
                "gross_wages": slip.gross_pay,
                "epf_wages":epf_wages,
                "eps_wages": eps_wages,
                "edli_wages": epf_wages,
                "ee_share_remitted": ee_share_remitted,
                "eps_contribution_remitted":eps_contribution_remitted,
                "er_share_remitted": ee_share_remitted - eps_contribution_remitted,
                "ncp_days": slip.leave_without_pay,
                "refund_of_advance": 0,
            }
            data.append(row)

    return columns, data
