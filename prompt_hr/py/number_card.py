import frappe

@frappe.whitelist()
def get_pending_records_for_user(filters):
    """
    FETCHES ALL PENDING RECORDS OF DOCTYPE FOR THE LOGGED-IN USER 
    AND OPTIONALLY FOR EMPLOYEES REPORTING TO THEM.
    
    RETURNS:
        INT: A LENGTH OF LIST OF DICTIONARIES CONTAINING DOCTYPE DETAILS.
    """
    if not filters:
        return

    if filters:
        filters = frappe.parse_json(filters)
    
    current_user = frappe.session.user
    if not current_user or current_user == "Guest":
        return []

    # ? GET THE EMPLOYEE LINKED TO THE CURRENT USER
    employee_id = frappe.db.get_value("Employee", {"user_id": current_user}, "name")
    if not employee_id:
        return []

    # Get employees who report to the current employee
    reporting_employees = frappe.get_all("Employee", {"reports_to": employee_id}, pluck="name")

    # Fetch pending records for the current employee
    user_pending_records = frappe.get_all(
        filters.get("doctype"),
        filters={
            "employee": employee_id,
            "workflow_state": "Pending",
        },
        fields=["name"],
    )

    # Fetch pending records for employees reporting to the current employee
    reporting_pending_records = frappe.get_all(
        filters.get("doctype"),
        filters={
            "employee": ["in", reporting_employees],
            "workflow_state": "Pending",
        },
        fields=["name"],
    )

    # Combine both lists
    all_pending_records = user_pending_records + reporting_pending_records
    # ? COMBINE EMPLOYEE AND ITS REPORTING EMPLOYEES
    all_employees = reporting_employees
    all_employees.append(employee_id)

    return {  
        "value": int(len(all_pending_records)),
        "fieldtype": "Int",  
        "route": ["List", filters.get("doctype"), {"employee": ["in", all_employees], "workflow_state": "Pending"}],
    }
