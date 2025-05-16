# Copyright (c) 2025, Jignasha Chavda and contributors
# For license information, please see license.txt

import frappe
from frappe.utils import getdate, flt


def execute(filters=None):
    """
    Execute the Salary Structure report.

    This function serves as the entry point for the Frappe Script Report, generating
    columns and data based on the provided filters.

    Args:
        filters (dict, optional): Filters to apply to the report data. Defaults to None.

    Returns:
        tuple: A tuple containing:
            - list: List of column definitions.
            - list: List of data rows for the report.
    """
    columns = get_columns()
    data = get_data(filters)
    message = "<h3>Prompt Equipments Pvt. Ltd.<h3><h4>Employee Current Salary - Monthly | Currency : INR</h4>"
    return columns, data, message


def get_columns():
    """
    Generate column definitions for the Salary Structure report.

    This function creates a list of column definitions, including fixed employee
    attributes and dynamic columns for salary components (earnings and deductions).
    The columns are formatted for display in the report.

    Returns:
        list: List of dictionaries, each defining a column's label, fieldname, fieldtype, and width.
    """
    # Fixed base columns for employee details
    columns = [
        {
            "label": "Employee Number",
            "fieldname": "employee_number",
            "fieldtype": "Data",
            "width": 120,
        },
        {"label": "Employee Name", "fieldname": "employee_name", "fieldtype": "Data", "width": 150},
        {
            "label": "Date of Joining",
            "fieldname": "date_of_joining",
            "fieldtype": "Date",
            "width": 100,
        },
        {"label": "Pay Group", "fieldname": "pay_group", "fieldtype": "Data", "width": 120},
        {
            "label": "Remuneration Type",
            "fieldname": "remuneration_type",
            "fieldtype": "Data",
            "width": 120,
        },
        {"label": "Employment Status", "fieldname": "status", "fieldtype": "Data", "width": 100},
        {"label": "Worker Type", "fieldname": "employment_type", "fieldtype": "Data", "width": 100},
        {"label": "Job Title", "fieldname": "designation", "fieldtype": "Data", "width": 120},
        {"label": "Department", "fieldname": "department", "fieldtype": "Data", "width": 120},
        {
            "label": "Sub Department",
            "fieldname": "custom_subdepartment",
            "fieldtype": "Data",
            "width": 120,
        },
        {"label": "Location", "fieldname": "custom_work_location", "fieldtype": "Data", "width": 100},
        {
            "label": "Business Unit",
            "fieldname": "custom_business_unit",
            "fieldtype": "Data",
            "width": 120,
        },
        {
            "label": "Cost Center",
            "fieldname": "payroll_cost_center",
            "fieldtype": "Link",
            "options": "Cost Center",
            "width": 120,
        },
        {
            "label": "Revision Effective From",
            "fieldname": "from_date",
            "fieldtype": "Date",
            "width": 100,
        },
        {"label": "Last Updated On", "fieldname": "modified", "fieldtype": "Datetime", "width": 100},
    ]

    # Fetch salary components once to avoid multiple database calls
    salary_components = frappe.get_all(
        "Salary Component", fields=["name", "type"], order_by="name"
    )

    # Add earning components as currency columns
    for comp in salary_components:
        if comp.type == "Earning":
            fieldname = comp.name.lower().replace(" ", "_").replace("&", "and").replace("-", "_")
            columns.append(
                {
                    "label": comp.name,
                    "fieldname": fieldname,
                    "fieldtype": "Currency",
                    "width": 120,
                }
            )

    # Add summary fields for gross and total
    columns.extend(
        [
            {"label": "Gross(A)", "fieldname": "gross", "fieldtype": "Currency", "width": 120},
            {"label": "Total", "fieldname": "total", "fieldtype": "Currency", "width": 120},
        ]
    )

    # Add deduction components as currency columns
    for comp in salary_components:
        if comp.type == "Deduction":
            fieldname = comp.name.lower().replace(" ", "_").replace("&", "and").replace("-", "_")
            columns.append(
                {
                    "label": comp.name,
                    "fieldname": fieldname,
                    "fieldtype": "Currency",
                    "width": 120,
                }
            )

    # Add net pay column
    columns.append({"label": "NET Pay", "fieldname": "net", "fieldtype": "Currency", "width": 120})

    return columns


def get_data(filters):
    """
    Fetch data for the Salary Structure report.

    This function retrieves employee data and their latest salary structure assignments,
    calculating earnings, deductions, gross, total, and net pay for each employee.
    The data is formatted to match the column definitions.

    Args:
        filters (dict): Filters to apply to the employee data.

    Returns:
        list: List of dictionaries, each representing a row of report data.
    """
    # Fetch all employees with necessary fields
    employees = frappe.get_all("Employee", fields=["name","employee_number", "employee_name", "date_of_joining", "status", "employment_type", "designation", "department", "custom_subdepartment", "custom_work_location", "custom_business_unit", "payroll_cost_center"])

    # Fetch salary components and create fieldname mappings
    salary_components = frappe.get_all("Salary Component", fields=["name", "type"])
    component_keys = [
        comp.name.lower().replace(" ", "_").replace("&", "and").replace("-", "_")
        for comp in salary_components
    ]

    data = []

    for emp in employees:
        # Fetch the latest salary structure assignment for the employee
        ssa = frappe.get_all(
            "Salary Structure Assignment",
            filters={"employee": emp.name, "docstatus": 1},
            fields=["name", "salary_structure", "from_date", "modified"],
            order_by="from_date desc",
            limit_page_length=1,
        )

        if not ssa:
            continue

        # Load salary structure assignment and its linked salary structure
        ssa_doc = frappe.get_doc("Salary Structure Assignment", ssa[0].name)
        salary_structure = frappe.get_doc("Salary Structure", ssa_doc.salary_structure)

        # Initialize salary components dictionary with zeros
        salary_components_dict = {key: 0 for key in component_keys}
        earnings = 0
        deductions = 0

        # Process earnings
        for comp in salary_structure.earnings:
            key = comp.salary_component.lower().replace(" ", "_").replace("&", "and").replace("-", "_")
            if key in salary_components_dict:
                amount = flt(comp.amount)
                salary_components_dict[key] = amount
                earnings += amount

        # Calculate gross and total (gross = earnings in this context)
        gross = earnings
        salary_components_dict.update({"gross": gross, "total": gross})

        # Process deductions
        for comp in salary_structure.deductions:
            key = comp.salary_component.lower().replace(" ", "_").replace("&", "and").replace("-", "_")
            if key in salary_components_dict:
                amount = flt(comp.amount)
                salary_components_dict[key] = amount
                deductions += amount

        # Calculate net pay
        net_pay = earnings - deductions
        salary_components_dict["net"] = net_pay

        # Combine employee data, salary structure details, and salary components
        data.append(
            {
                **emp,  # Employee fields
                "from_date": ssa_doc.from_date,
                "modified": ssa_doc.modified,
                **salary_components_dict,  # Salary component amounts
            }
        )

    return data