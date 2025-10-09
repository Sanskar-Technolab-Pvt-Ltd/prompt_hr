# Copyright (c) 2025, Jignasha Chavda and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document

class OrganizationDocuments(Document):
    pass
	

def get_permission_query_conditions(user):
    # Allow full access for Administrator
    if user == "Administrator":
        return "1=1"

    #  Check roles of the user
    user_roles = frappe.get_roles(user)
    hr_roles = [
        "S - HR Director (Global Admin)",
        "S - HR L1",
        "S - HR L2",
        "S - HR L3",
        "S - HR L4",
        "S - HR L5",
        "S - HR L6"
    ]
    
     #  If user has S - Employee and at least one HR role → Full access
    if "S - Employee" in user_roles and any(role in user_roles for role in hr_roles):
        return "1=1"
    
    # Get employee linked with current user
    employee = frappe.db.get_value("Employee", {"user_id": user}, "name")
    if not employee:
        return "1=2"  # deny all if not linked
    
    # Prepare employee field values once to avoid repeated DB hits
    emp_data = frappe.db.get_value(
        "Employee",
        employee,
        ["department", "designation", "grade", "employment_type", "custom_work_location"],
        as_dict=True
    )
 

    docs_with_access = []

    # Only fetch documents where is_published = 1
    all_docs = frappe.get_all(
        "Organization Documents",
        filters={"is_published": 1},
        fields=["name"],
        ignore_permissions=True
    )

	
    for doc in all_docs:
        access_rows = frappe.get_all(
            "Access Criteria",
            filters={"parent": doc.name},
            fields=["select_doctype", "value"]
        )

        # If no criteria, allow access
        if not access_rows:
            docs_with_access.append(doc.name)
            continue

        # Loop through multiple access criteria for this document
        for row in access_rows:
            if row.select_doctype == "Department" and emp_data.get("department") == row.value:
                docs_with_access.append(doc.name)
                break
                
            elif row.select_doctype == "Designation" and emp_data.get("designation") == row.value:
                docs_with_access.append(doc.name)
                break

            elif row.select_doctype == "Employee Grade" and emp_data.get("grade") == row.value:
                docs_with_access.append(doc.name)
                break

            elif row.select_doctype == "Employment Type" and emp_data.get("employment_type") == row.value:
                docs_with_access.append(doc.name)
                break
                
            elif row.select_doctype == "Address" and emp_data.get("custom_work_location") == row.value:
                docs_with_access.append(doc.name)
                break

    if docs_with_access:
        allowed_docs = "', '".join(docs_with_access)
        return f"`tabOrganization Documents`.`name` IN ('{allowed_docs}')"
    else:
        return "1=2"
