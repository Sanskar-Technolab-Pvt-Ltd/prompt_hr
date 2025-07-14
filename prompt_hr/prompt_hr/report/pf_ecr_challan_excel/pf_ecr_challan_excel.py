# Copyright (c) 2025, Jignasha Chavda and contributors
# For license information, please see license.txt

import frappe
from frappe.utils import get_datetime, getdate
import calendar

def execute(filters=None):
    month = frappe.utils.getdate(filters.get("month")).month
    year = int(get_datetime().year)

    # Set the start and end date for the selected month
    from_date = getdate(f"{year}-{month:02d}-01")
    last_day = calendar.monthrange(year, month)[1]
    to_date = getdate(f"{year}-{month:02d}-{last_day}")

    columns = [
        {"label": "UAN", "fieldname": "employee_number", "fieldtype": "Data", "width": 120},
        {"label": "MEMBER NAME", "fieldname": "employee_name", "fieldtype": "Data", "width": 180},
        {"label": "GROSS WAGES", "fieldname": "gross_wages", "fieldtype": "Currency", "width": 120},
        {"label": "EPF WAGES", "fieldname": "epf_wages", "fieldtype": "Currency", "width": 120},
        {"label": "EPS WAGES", "fieldname": "eps_wages", "fieldtype": "Currency", "width": 120},
        {"label": "EDLI WAGES", "fieldname": "edli_wages", "fieldtype": "Currency", "width": 120},
        {"label": "EE SHARE REMITTED", "fieldname": "ee_share_remitted", "fieldtype": "Currency", "width": 150},
        {"label": "EPS CONTRIBUTION REMITTED", "fieldname": "eps_contribution_remitted", "fieldtype": "Currency", "width": 180},
        {"label": "ER SHARE REMITTED", "fieldname": "er_share_remitted", "fieldtype": "Currency", "width": 150},
        {"label": "NCP DAYS", "fieldname": "ncp_days", "fieldtype": "Int", "width": 100},
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
    if filters.get("employee"):
        salary_filters["employee"] = filters.get("employee")

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
            fields=["salary_component", "amount"],

        )
        # house_rent_allowance = 0
        # telephone_allowance = 0
        # food_coupons = 0
        # performance_bonus = 0
        # lta = 0
        # medical_allowance = 0
        # internet_allowance  = 0
        basic = 0
        dearness_allowance = 0
        if salary_details:
            for salary_detail in salary_details:
                salary_comp = frappe.get_doc("Salary Component", salary_detail.salary_component)
                # if salary_comp.custom_salary_component_type == "House Rent Allowance":
                #     house_rent_allowance += salary_detail.amount
                # elif salary_comp.custom_salary_component_type == "LTA":
                #     lta += salary_detail.amount
                # elif salary_comp.custom_salary_component_type == "Medical Allowance":
                #     medical_allowance += salary_detail.amount
                # elif salary_comp.custom_salary_component_type == "Mobile & Internet Allowance":
                #     internet_allowance += salary_detail.amount
                if salary_comp.custom_salary_component_type == "Basic Salary":
                    basic += salary_detail.amount
                elif salary_comp.custom_salary_component_type == "Dearness Allowance":
                    dearness_allowance += salary_detail.amount
                # elif salary_comp.custom_salary_component_type == "Food coupons Deduction":
                #     food_coupons += salary_detail.amount
                # elif salary_comp.custom_salary_component_type == "Performance Bonus":
                #     performance_bonus += salary_detail.amount
                # elif salary_comp.custom_salary_component_type == "Telephone Reimbursement":
                #     telephone_allowance += salary_detail.amount
        
        epf_wages = basic + dearness_allowance
        # eps_wages =  slip.gross_pay - lta - medical_allowance - internet_allowance - telephone_allowance - performance_bonus - food_coupons - house_rent_allowance
        if epf_wages > 15000:
            eps_wages = 15000
        else:
            eps_wages = epf_wages
        ee_share_remitted = epf_wages * 0.12
        eps_contribution_remitted = eps_wages * 0.0833
        row = {
            "employee_number": employee.custom_uan_number,
            "employee_name": employee.employee_name,
            "gross_wages": slip.gross_pay,
            "epf_wages":epf_wages,
            "eps_wages": eps_wages,
            "edli_wages": epf_wages,
            "ee_share_remitted": ee_share_remitted,
            "eps_contribution_remitted":eps_contribution_remitted,
            "er_share_remitted": ee_share_remitted - eps_contribution_remitted,
            "ncp_days": slip.leave_without_pay,
            "refund_of_advance": "",
        }
        data.append(row)

    return columns, data
