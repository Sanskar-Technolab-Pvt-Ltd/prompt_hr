# # Copyright (c) 2025, Jignasha Chavda and contributors
# # For license information, please see license.txt

# import frappe

# def execute(filters=None):
#     filters = filters or {}
#     columns = get_columns()
#     data = get_data(filters)
#     return columns, data


# def get_columns():
#     return [
#         {"label": "Project Name", "fieldname": "project_name", "fieldtype": "Data", "width": 200},
#         {"label": "Project Code", "fieldname": "project_code", "fieldtype": "Data", "width": 120},
#         {"label": "Project Status", "fieldname": "project_status", "fieldtype": "Data", "width": 120},

#         {"label": "Employee ID", "fieldname": "employee_id", "fieldtype": "Link", "options": "Employee", "width": 120},
#         {"label": "Employee Name", "fieldname": "employee_name", "fieldtype": "Data", "width": 180},
#         {"label": "Business Unit", "fieldname": "business_unit", "fieldtype": "Data", "width": 140},
#         {"label": "Department", "fieldname": "department", "fieldtype": "Data", "width": 140},
#         {"label": "Sub-Department", "fieldname": "sub_department", "fieldtype": "Data", "width": 140},
#         {"label": "Work Location", "fieldname": "work_location", "fieldtype": "Data", "width": 140},
#         {"label": "Reporting To", "fieldname": "reporting_to", "fieldtype": "Data", "width": 150},
# 		{"label": "Reporting Manager Name", "fieldname": "reporting_manager_name", "fieldtype": "Data", "width": 150},
  
#         {"label": "Billable Hours", "fieldname": "billable_hours", "fieldtype": "Float", "width": 130},
#         {"label": "Billing Rate (Per Hour)", "fieldname": "billing_rate", "fieldtype": "Currency", "width": 150},
#         {"label": "Billing Amount", "fieldname": "billing_amount", "fieldtype": "Currency", "width": 150},
#     ]


# def get_data(filters):
# 	data = []
# 	project_filter = filters.get("project")
# 	start_date = filters.get("start_date")
# 	end_date = filters.get("end_date")

# 	projects = frappe.get_all(
# 		"Project",
# 		fields=["name", "project_name", "status"],
# 		filters={"name": project_filter, "status": ["!=", "Cancelled"]} if project_filter else {"status": ["!=", "Cancelled"]}
# 	)

# 	# print(f"\n\n PROJECTS {projects}\n\n")

# 	for proj in projects:
# 		total_hours = 0.0
# 		total_amount = 0.0
# 		rates = 0.0
# 		has_rows = False

# 		# employees from Project User
# 		project_users = frappe.get_all(
# 			"Project User",
# 			filters={"parent": proj.name},
# 			fields=["custom_employee as employee"]
# 		)

# 		print(f"\n\n project user {project_users} \n\n")
# 		for pu in project_users:
# 			emp = frappe.db.get_value(
# 				"Employee",
# 				pu.employee,
# 				[
# 					"name",
# 					"employee_name",
# 					"custom_business_unit",
# 					"department",
# 					"custom_subdepartment",
# 					"custom_work_location",
# 					"reports_to"
# 				],
# 				as_dict=True
# 			)

# 			if not emp:
# 				continue

# 			# Step 1: get timesheets for employee
# 			ts_filters = {"employee": emp.name}
# 			if start_date and end_date:
# 				ts_filters["custom_date"] = [">=", start_date]
# 				ts_filters["custom_date"] = ["<=", end_date]

# 			timesheets = frappe.get_all("Timesheet", filters=ts_filters, pluck="name")
# 			if not timesheets:
# 				continue

# 			# Step 2: sum time logs from those timesheets that belong to this project
# 			time_logs = frappe.db.sql("""
# 				SELECT 
# 					SUM(billing_hours) AS total_hours,
# 					billing_rate,
# 					SUM(billing_amount) AS total_amount
# 				FROM `tabTimesheet Detail`
# 				WHERE parent IN %(timesheets)s
# 				AND project = %(project)s
# 			""", {"timesheets": tuple(timesheets), "project": proj.name}, as_dict=True)

# 			if not time_logs or not time_logs[0].total_hours:
# 				continue
			
# 			print(f"\n\n TIME LOGS {time_logs}\n\n")
# 			row = time_logs[0]
# 			hours = row.total_hours or 0.0
# 			rate = row.billing_rate or 0.0
# 			amount = row.total_amount or 0.0

# 			reporting_manager_name = frappe.db.get_value("Employee", emp.reports_to, "employee_name") or ""
# 			data.append({
# 				"project_name": proj.project_name,
# 				"project_code": proj.name,
# 				"project_status": proj.status,

# 				"employee_id": emp.name,
# 				"employee_name": emp.employee_name,
# 				"business_unit": emp.custom_business_unit,
# 				"department": emp.department,
# 				"sub_department": emp.custom_subdepartment,
# 				"work_location": emp.custom_work_location,
# 				"reporting_to": emp.reports_to,
# 				"reporting_manager_name": reporting_manager_name,
    
# 				"billable_hours": hours,
# 				"billing_rate": rate,
# 				"billing_amount": amount
# 			})

# 			has_rows = True
# 			total_hours += hours
# 			total_amount += amount
# 			rates += rate

# 		# total row
# 		if has_rows:
# 			# avg_rate = (sum(rates) / len(rates)) if rates else 0.0
# 			data.append({
# 				"project_name": f"Total ({proj.project_name})",
# 				"project_code": "",
# 				"project_status": "",

# 				"employee_id": "",
# 				"employee_name": "",
# 				"business_unit": "",
# 				"department": "",
# 				"sub_department": "",
# 				"work_location": "",
# 				"reporting_to": "",

# 				"billable_hours": total_hours,
# 				"billing_rate": rates,
# 				"billing_amount": total_amount
# 			})

# 	return data


# Copyright (c) 2025, Jignasha Chavda and contributors
# For license information, please see license.txt

import frappe


def execute(filters=None):
    filters = filters or {}
    columns = get_columns()
    data = get_data(filters)
    return columns, data


def get_columns():
    return [
        {"label": "Project Name", "fieldname": "project_name", "fieldtype": "Data", "width": 200},
        {"label": "Project Code", "fieldname": "project_code", "fieldtype": "Data", "width": 120},
        {"label": "Project Status", "fieldname": "project_status", "fieldtype": "Data", "width": 120},

        {"label": "Employee ID", "fieldname": "employee_id", "fieldtype": "Link", "options": "Employee", "width": 120},
        {"label": "Employee Name", "fieldname": "employee_name", "fieldtype": "Data", "width": 180},
        {"label": "Business Unit", "fieldname": "business_unit", "fieldtype": "Data", "width": 140},
        {"label": "Department", "fieldname": "department", "fieldtype": "Data", "width": 140},
        {"label": "Sub-Department", "fieldname": "sub_department", "fieldtype": "Data", "width": 140},
        {"label": "Work Location", "fieldname": "work_location", "fieldtype": "Data", "width": 140},
        {"label": "Reporting To", "fieldname": "reporting_to", "fieldtype": "Data", "width": 150},
        {"label": "Reporting Manager Name", "fieldname": "reporting_manager_name", "fieldtype": "Data", "width": 150},

        {"label": "Billable Hours", "fieldname": "billable_hours", "fieldtype": "Float", "width": 130},
        {"label": "Billing Rate (Per Hour)", "fieldname": "billing_rate", "fieldtype": "Currency", "width": 150},
        {"label": "Billing Amount", "fieldname": "billing_amount", "fieldtype": "Currency", "width": 150},
    ]


def get_data(filters):
    data = []
    project_filter = filters.get("project")
    start_date = filters.get("start_date")
    end_date = filters.get("end_date")

    projects = frappe.get_all(
        "Project",
        fields=["name", "project_name", "status"],
        filters={"name": project_filter, "status": ["!=", "Cancelled"]} if project_filter else {"status": ["!=", "Cancelled"]}
    )

    for proj in projects:
        project_rows = []
        total_hours = 0.0
        total_amount = 0.0
        total_rate = 0.0
        has_rows = False

        # employees from Project User
        project_users = frappe.get_all(
            "Project User",
            filters={"parent": proj.name},
            fields=["custom_employee as employee"]
        )

        for pu in project_users:
            emp = frappe.db.get_value(
                "Employee",
                pu.employee,
                [
                    "name",
                    "employee_name",
                    "custom_business_unit",
                    "department",
                    "custom_subdepartment",
                    "custom_work_location",
                    "reports_to"
                ],
                as_dict=True
            )

            if not emp:
                continue

            # Step 1: get timesheets for employee
            ts_filters = {"employee": emp.name}
            if start_date and end_date:
                ts_filters["custom_date"] = [">=", start_date]
                ts_filters["custom_date"] = ["<=", end_date]

            timesheets = frappe.get_all("Timesheet", filters=ts_filters, pluck="name")
            if not timesheets:
                continue

            # Step 2: sum time logs from those timesheets that belong to this project
            time_logs = frappe.db.sql("""
                SELECT 
                    SUM(billing_hours) AS total_hours,
                    billing_rate,
                    SUM(billing_amount) AS total_amount
                FROM `tabTimesheet Detail`
                WHERE parent IN %(timesheets)s
                AND project = %(project)s
            """, {"timesheets": tuple(timesheets), "project": proj.name}, as_dict=True)

            if not time_logs or not time_logs[0].total_hours:
                continue

            row = time_logs[0]
            hours = row.total_hours or 0.0
            rate = row.billing_rate or 0.0
            amount = row.total_amount or 0.0

            reporting_manager_name = frappe.db.get_value("Employee", emp.reports_to, "employee_name") or ""

            project_rows.append({
                "project_name": proj.project_name,
                "project_code": proj.name,
                "project_status": proj.status,

                "employee_id": emp.name,
                "employee_name": emp.employee_name,
                "business_unit": emp.custom_business_unit,
                "department": emp.department,
                "sub_department": emp.custom_subdepartment,
                "work_location": emp.custom_work_location,
                "reporting_to": emp.reports_to,
                "reporting_manager_name": reporting_manager_name,

                "billable_hours": hours,
                "billing_rate": rate,
                "billing_amount": amount
            })

            has_rows = True
            total_hours += hours
            total_amount += amount
            total_rate += rate

        # Format for grouped visual layout
        for idx, row in enumerate(project_rows):
            if idx > 0:
                row["project_name"] = ""
                row["project_code"] = ""
                row["project_status"] = ""

        # total row
        if has_rows:
            project_rows.append({
                "project_name": f"Total ({proj.project_name})",
                "project_code": "",
                "project_status": "",

                "employee_id": "",
                "employee_name": "",
                "business_unit": "",
                "department": "",
                "sub_department": "",
                "work_location": "",
                "reporting_to": "",
                "reporting_manager_name": "",

                "billable_hours": total_hours,
                "billing_rate": total_rate,  # keep same as your code (sum, not avg)
                "billing_amount": total_amount
            })

        data.extend(project_rows)

    return data
