

import frappe
from frappe import _
import traceback

def create_welcome_status(doc, method):
    """Create a welcome status record for new users"""
    try:
        # Check if record already exists
        existing = frappe.db.exists("Welcome Page", {"user": doc.name})
        if existing:
            frappe.log_error(f"Welcome Page for user {doc.name} already exists. Skipping creation.")
            return
            
        welcome_status = frappe.new_doc("Welcome Page")
        welcome_status.user = doc.name
        welcome_status.is_completed = 0
        welcome_status.insert(ignore_permissions=True)
        
        frappe.db.commit()
        frappe.log_error(f"Welcome Page created successfully for user {doc.name}", "Welcome Page Creation")
    except Exception as e:
        frappe.log_error(f"Error creating Welcome Page for user {doc.name}: {str(e)}\n{traceback.format_exc()}", 
                        "Welcome Page Creation Error")

def check_welcome_completion(user):
    try:
        if not user:
            user = frappe.session.user
            
        # System Manager can access everything
        if user == "Administrator" or "System Manager" in frappe.get_roles(user):
            return ""
            
        # Check if welcome form is completed
        is_completed = frappe.db.get_value("Welcome Page", {"user": user}, "is_completed")
        
        frappe.log_error(f"User: {user}, Is Completed: {is_completed}", "Welcome Page Check")
        
        if not is_completed:
            # Only allow access to welcome page and core system doctypes
            allowed_doctypes = ["Welcome Page", "User", "File", "Custom Field", "Property Setter"]
            allowed_doctypes_condition = f"name in ({', '.join(['%s'] * len(allowed_doctypes))})"
            
            frappe.log_error(f"Restricting access for user {user}. Allowed doctypes: {allowed_doctypes}", 
                           "Welcome Page Access Check")
            
            return allowed_doctypes_condition, allowed_doctypes
        
        return ""
    except Exception as e:
        frappe.log_error(f"Error in check_welcome_completion for user {user}: {str(e)}\n{traceback.format_exc()}", 
                        "Welcome Page Check Error")
        return ""  # Default to not restricting access in case of errors