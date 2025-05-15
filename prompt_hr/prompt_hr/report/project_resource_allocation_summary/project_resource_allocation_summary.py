# Copyright (c) 2025, Jignasha Chavda and contributors
# For license information, please see license.txt

import frappe
from frappe.utils import getdate

def execute(filters=None):
    columns = [
        {"label": "Client Name", "fieldname": "client_name", "fieldtype": "Data", "width": 120},
        {"label": "Client Code", "fieldname": "client_code", "fieldtype": "Data", "width": 100},
        {"label": "Project Name", "fieldname": "project_name", "fieldtype": "Data", "width": 150},
        {"label": "Project Code", "fieldname": "project_code", "fieldtype": "Data", "width": 100},
        {"label": "Project Managers", "fieldname": "project_managers", "fieldtype": "Data", "width": 150},
        {"label": "Project State", "fieldname": "project_state", "fieldtype": "Data", "width": 100},
        {"label": "Employee Number", "fieldname": "employee", "fieldtype": "Link", "options": "Employee", "width": 120},
        {"label": "Employee Name", "fieldname": "employee_name", "fieldtype": "Data", "width": 150},
        {"label": "Department", "fieldname": "department", "fieldtype": "Data", "width": 120},
        {"label": "Sub Department", "fieldname": "sub_department", "fieldtype": "Data", "width": 120},
        {"label": "Business Unit", "fieldname": "business_unit", "fieldtype": "Data", "width": 120},
        {"label": "Job Title", "fieldname": "job_title", "fieldtype": "Data", "width": 120},
        {"label": "Location", "fieldname": "location", "fieldtype": "Data", "width": 100},
        {"label": "Employment Status", "fieldname": "employment_status", "fieldtype": "Data", "width": 130},
        {"label": "Reporting To", "fieldname": "reporting_to", "fieldtype": "Data", "width": 130},
        {"label": "Start Date", "fieldname": "start_date", "fieldtype": "Date", "width": 100},
        {"label": "End Date", "fieldname": "end_date", "fieldtype": "Date", "width": 100},
        {"label": "Allocation Percentage", "fieldname": "allocation_percentage", "fieldtype": "Float", "width": 100},
        {"label": "Project Start Date", "fieldname": "project_start_date", "fieldtype": "Date", "width": 120},
        {"label": "Project End Date", "fieldname": "project_end_date", "fieldtype": "Date", "width": 120},
        {"label": "Billing Role", "fieldname": "billing_role", "fieldtype": "Data", "width": 100},
        {"label": "Billing Rate", "fieldname": "billing_rate", "fieldtype": "Currency", "width": 100},
    ]

    timesheets = frappe.get_all("Timesheet", 
        fields=["name", "parent_project", "employee", "employee_name", "department", "start_date", "end_date"],
        filters={"docstatus": 1},
    )

    data = []
    for ts in timesheets:
        project = frappe.get_all("Project", 
            filters={"name": ts.parent_project},
            fields=["project_name", "name as project_code", "status as project_state", "expected_start_date", "expected_end_date"],
        )

        p = project[0] if project else {}

        data.append({
            "client_name": "HR",  # Default value
            "client_code": "PSC10",  # Default value
            "project_name": p.get("project_name", "N/A"),
            "project_code": p.get("project_code", ts.parent_project),
            "project_managers": "Anar Shah",  # Default
            "project_state": p.get("project_state", "Unknown"),
            "employee": ts.employee,
            "employee_name": ts.employee_name,
            "department": ts.department or "Software",  # Default
            "sub_department": "Embedded",  # Default
            "business_unit": "HO + PS",  # Default
            "job_title": "Sr. Project Manager",  # Default
            "location": "HO",  # Default
            "employment_status": "Working",  # Default
            "reporting_to": "Ritesh Ashokbhai Sutaria",  # Default
            "start_date": ts.start_date,
            "end_date": ts.end_date,
            "allocation_percentage": 100,  # Default
            "project_start_date": p.get("expected_start_date"),
            "project_end_date": p.get("expected_end_date"),
            "billing_role": "Dev (Web)",  # Default
            "billing_rate": 1.0  # Default
        })

    return columns, data
