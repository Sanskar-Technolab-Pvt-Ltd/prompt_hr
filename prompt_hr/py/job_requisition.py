import frappe

@frappe.whitelist()
def on_update(doc, method):
    print(f"\n\n both are getting called\n\n")
    if doc.custom_target_hiring_duration:
        if doc.custom_target_hiring_duration == "Custom Date":
            doc.custom_target_hiring_date = doc.expected_by if doc.expected_by else frappe.utils.nowdate()
        else:
            days = int(doc.custom_target_hiring_duration.split()[0]) if doc.custom_target_hiring_duration else 0
            doc.custom_target_hiring_date = frappe.utils.add_days(doc.posting_date, days)


@frappe.whitelist()
def add_or_update_custom_last_updated_by(doc, method):
    try:
        if doc.modified_by:
            employee_id = frappe.get_value("Employee", {"user_id": doc.modified_by}, "name")
            
            if employee_id:
                employee_name = frappe.get_value("Employee", employee_id, "employee_name")
                doc.custom_last_updated_by_employee = employee_id
                doc.custom_employee_name = employee_name
            else:
                doc.custom_last_updated_by_employee = None
                doc.custom_employee_name = None
                
    except Exception as e:
        frappe.log_error(f"Error in add_or_update_custom_last_updated_by: {str(e)}", "Job Requisition")
    