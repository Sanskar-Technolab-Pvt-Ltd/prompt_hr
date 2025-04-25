import frappe

@frappe.whitelist()
def on_update(doc, method):
    if doc.custom_target_hiring_duration:
        if doc.custom_target_hiring_duration == "Custom Date":
            doc.db_set("custom_target_hiring_date", doc.expected_by if doc.expected_by else frappe.utils.nowdate())
        else:
            try:
                days = int(doc.custom_target_hiring_duration.split()[0])
            except (ValueError, IndexError):
                days = 0
            doc.db_set("custom_target_hiring_date", frappe.utils.add_days(doc.posting_date, days))

@frappe.whitelist()
def add_or_update_custom_last_updated_by(doc, method):
    """ Method to set custom_last_updated_by_employee and custom_employee_name fields in Job Requisition to recognize the last user who modified the document.
    """
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
    

def set_requested_by(doc, event):
    """ Method to set requested_by field in Job Requisition if not set
    """
    try:
        if not doc.requested_by:
            user = frappe.session.user
            employee_id = frappe.get_value("Employee", {"user_id": user}, "name")
            
            if employee_id:
                employee_name = frappe.get_value("Employee", employee_id, "employee_name")
                doc.requested_by = employee_id
                doc.requested_by_name = employee_name
# 
    except Exception as e:
        frappe.log_error(f"Error in set_requested_by Job Requisition", frappe.get_traceback())