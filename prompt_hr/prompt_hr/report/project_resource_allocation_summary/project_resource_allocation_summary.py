# Copyright (c) 2025, Jignasha Chavda and contributors
# For license information, please see license.txt

import frappe
from frappe.utils import getdate

def execute(filters=None):
    
    filters = filters or {}
    
    print(f"\n\n helloooooo \n\n")
    
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
        # {"label": "Allocation Percentage", "fieldname": "allocation_percentage", "fieldtype": "Float", "width": 100},
        {"label": "Project Start Date", "fieldname": "project_start_date", "fieldtype": "Date", "width": 120},
        {"label": "Project End Date", "fieldname": "project_end_date", "fieldtype": "Date", "width": 120},
        # {"label": "Billing Role", "fieldname": "billing_role", "fieldtype": "Data", "width": 100},
        # {"label": "Billing Rate", "fieldname": "billing_rate", "fieldtype": "Currency", "width": 100},
    ]

    start_date = getdate(filters.get("start_date")) if filters.get("start_date") else None
    end_date = getdate(filters.get("end_date")) if filters.get("end_date") else None
    project_filter = filters.get("project")
    
    project_conditions = {"status": ["!=", "Cancelled"]}
    if project_filter:
        project_conditions["name"] = project_filter
    
    project_details = frappe.db.get_all("Project", filters=project_conditions, fields = ["customer as client_code", "project_name", "name as project_code", "custom_project_coordinator as project_managers", "status as project_state", "custom_start_date as project_start_date", "custom_end_date as project_end_date"])
        
    data = []
    for project_dt in project_details:
        
        customer_name = ""
        if project_dt.get("client_code"):
            customer_name = frappe.db.get_value("Customer", project_dt.get("client_code"), "customer_name")
        
        # user_details = frappe.db.get_all("Project User",{"parenttype": "Project", "parent": project_dt.get("project_code")}, ["custom_employee", "full_name", "custom_from_date", "custom_to_date"])
        user_filters = {"parenttype": "Project", "parent": project_dt.get("project_code")}
        user_details = frappe.db.get_all(
            "Project User",
            filters=user_filters,
            fields=["custom_employee", "full_name", "custom_from_date", "custom_to_date"]
        )
        
        if not user_details:
            print(f"\n\n No Data \n\n")
            continue
        
        if user_details:
            for user_dt in user_details:
               # Apply date filter logic (if provided)
                from_date = getdate(user_dt.get("custom_from_date")) if user_dt.get("custom_from_date") else None
                to_date = getdate(user_dt.get("custom_to_date")) if user_dt.get("custom_to_date") else None

                if start_date and end_date:
                    # Apply date overlap filter
                    if (from_date and from_date > end_date) or (to_date and to_date < start_date):
                        continue
                row = {
                    "client_name": customer_name or "",
                    "client_code": project_dt.get("client_code"),
                    "project_name": project_dt.get("project_name"),
                    "project_code": project_dt.get("project_code"),
                    "project_managers": project_dt.get("project_managers"),
                    "project_state": project_dt.get("project_state"),
                    "start_date": from_date,
                    "end_date": to_date,
                    "project_start_date": project_dt.get("project_start_date"),
                    "project_end_date": project_dt.get("project_end_date"),
                }

                # Add employee details
                emp_id = user_dt.get("custom_employee")
                if emp_id and frappe.db.exists("Employee", emp_id):
                    emp_details = frappe.db.get_value(
                        "Employee",
                        emp_id,
                        ["department", "custom_subdepartment", "custom_business_unit",
                        "designation", "custom_work_location", "status", "reports_to"],
                        as_dict=True
                    )

                    row.update({
                        "employee": emp_id,
                        "employee_name": user_dt.get("full_name"),
                        "department": emp_details.get("department"),
                        "sub_department": emp_details.get("custom_subdepartment"),
                        "business_unit": emp_details.get("custom_business_unit"),
                        "job_title": emp_details.get("designation"),
                        "location": emp_details.get("custom_work_location"),
                        "employment_status": emp_details.get("status"),
                        "reporting_to": emp_details.get("reports_to"),
                    })

                
                data.append(row)
        
        
          

        # p = project[0] if project else {}
        # employee = frappe.get_doc("Employee", ts.employee)
        # data.append({
        #     "client_name": "HR",  # Default value
        #     "client_code": "PSC10",  # Default value
        #     "project_name": p.get("project_name", "N/A"),
        #     "project_code": p.get("project_code", ts.parent_project),
        #     "project_managers": "Anar Shah",  # Default
        #     "project_state": p.get("project_state", "Unknown"),
        #     "employee": ts.employee,
        #     "employee_name": ts.employee_name,
        #     "department": ts.department,
        #     "sub_department": employee.custom_subdepartment,
        #     "business_unit": employee.custom_business_unit,
        #     "job_title": employee.designation,
        #     "location": frappe.get_value("Address",employee.custom_work_location,"city"),
        #     "employment_status": "Working",
        #     "reporting_to": frappe.get_value("Employee", employee.reports_to, "employee_name"),
        #     "start_date": p.get("expected_start_date"),
        #     "end_date": p.get("expected_end_date"),
        #     "allocation_percentage": 100,  # Default
        #     "project_start_date": p.get("expected_start_date"),
        #     "project_end_date": p.get("expected_end_date"),
        #     "billing_role": "Dev (Web)",  # Default
        #     "billing_rate": 1.0  # Default
        # })
    print(f"\n\n DATA {data} \n\n")
    return columns, data
