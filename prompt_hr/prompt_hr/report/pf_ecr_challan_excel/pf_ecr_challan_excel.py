# Copyright (c) 2025, Jignasha Chavda and contributors
# For license information, please see license.txt

import frappe

def execute(filters=None):
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
        {"label": "REFUND OF ADVANCE", "fieldname": "refund_of_advance", "fieldtype": "Currency", "width": 150},
    ]

    # Set your static values here
    static_values = {
        "gross_wages": 15000,
        "epf_wages": 1800,
        "eps_wages": 1250,
        "edli_wages": 15000,
        "ee_share_remitted": 1800,
        "eps_contribution_remitted": 1250,
        "er_share_remitted": 1800,
        "ncp_days": 0,
        "refund_of_advance": 0,
    }

    # Fetch Employee Name and Number from Salary Slip
    data = []
    filters.setdefault("docstatus", 1)
    
    salary_slips = frappe.get_all(
        "Salary Slip",
        fields=["employee", "employee_name"],
        filters=filters or {}
    )

    for slip in salary_slips:
        employee = frappe.get_doc("Employee", slip.employee)
        row = {
            "employee_number": employee.custom_uan_number,
            "employee_name": employee.employee_name,
        }
        row.update(static_values)
        data.append(row)

    return columns, data