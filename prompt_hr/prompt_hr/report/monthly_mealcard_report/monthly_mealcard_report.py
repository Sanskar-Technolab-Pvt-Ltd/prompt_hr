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
            "label": "STAFF ID",
            "fieldname": "employee",
            "fieldtype": "Link",
            "options": "Employee",
            "width": 100,
        },
        {
            "label": "Name",
            "fieldname": "employee_name",
            "fieldtype": "Data",
            "width": 160,
        },
        {
            "label": "Mobile Number",
            "fieldname": "mobile_no",
            "fieldtype": "Data",
            "width": 130,
        },
        {
            "label": "Corporate ID",
            "fieldname": "corporate_id",
            "fieldtype": "Data",
            "width": 130,
        },
        {
            "label": "Card No",
            "fieldname": "meal_card_no",
            "fieldtype": "Data",
            "width": 130,
        },
        {
            "label": "Ref No",
            "fieldname": "meal_card_ref_no",
            "fieldtype": "Data",
            "width": 130,
        },
        {
            "label": "Remarks",
            "fieldname": "remarks",
            "fieldtype": "Data",
            "width": 140,
        },
        {
            "label": "Handover On",
            "fieldname": "handover_on",
            "fieldtype": "Date",
            "width": 120,
        },
        {
            "label": "Meal Wallet Amount",
            "fieldname": "meal_wallet_amount",
            "fieldtype": "Currency",
            "width": 160,
        },
        {
            "label": "Fuel Wallet Amount",
            "fieldname": "fuel_wallet_amount",
            "fieldtype": "Currency",
            "width": 160,
        },
        {
            "label": "Attire Wallet Amount",
            "fieldname": "attire_wallet_amount",
            "fieldtype": "Currency",
            "width": 180,
        },
        {
            "label": "Telecom Wallet Amount",
            "fieldname": "telecom_wallet_amount",
            "fieldtype": "Currency",
            "width": 200,
        }
    ]

def get_data(filters):
    # Set the start and end date for the selected month
    from_date = getdate(filters.get("from_date"))
    to_date = getdate(filters.get("to_date"))
    corporate_id_for_meal_card = frappe.db.get_single_value("HR Settings", "custom_corporate_id_for_meal_card")

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
            filters={
                "parent": slip.name,
            },
            fields=["salary_component", "amount"]
        )

        meal_amount = 0
        fuel_amount = 0
        attire_amount = 0
        telecom_amount = 0

        for detail in salary_details:
            salary_comp = frappe.get_doc("Salary Component", detail.salary_component)
            if salary_comp.custom_salary_component_type == "Fuel Coupan - Deduction":
                fuel_amount += detail.amount
            elif salary_comp.custom_salary_component_type == "Professional Attire Coupan - Deduction":
                attire_amount += detail.amount
            elif salary_comp.custom_salary_component_type == "Meal Coupan - Deduction":
                meal_amount += detail.amount
            elif salary_comp.custom_salary_component_type == "Telephone Coupan - Deduction":
                telecom_amount += detail.amount

        if (
            employee.status == "Active"
            and (
                employee.custom_telephone_reimbursement_applicable
                or employee.custom_fuel_card_consent
                or employee.custom_attire_card_consent
                or employee.custom_meal_card_consent
            )
        ):
            mobile_no = (
                employee.cell_number
                if employee.custom_preferred_mobile == "Personal Mobile No"
                else employee.custom_work_mobile_no
            )

            row = {
                "employee": slip.employee,
                "employee_name": slip.employee_name,
                "mobile_no": mobile_no,
                "corporate_id": corporate_id_for_meal_card or "",
                "meal_card_no": employee.custom_mealcard_number or "",
                "meal_card_ref_no": employee.custom_mealcard_ref_number or "",
                "remarks": "",
                "handover_on": "",
                "attire_wallet_amount": attire_amount,
                "fuel_wallet_amount": fuel_amount,
                "meal_wallet_amount": meal_amount,
                "telecom_wallet_amount": telecom_amount
            }
            data.append(row)

    return data
