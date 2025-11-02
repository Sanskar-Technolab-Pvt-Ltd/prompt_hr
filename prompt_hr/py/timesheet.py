import frappe

# * IF THE USER IS PROJEC CO-ORDINATOR OR HAS ANY OF THE HR MANAGER ROLES THEN RETURNING 1 ELSE O
@frappe.whitelist()
def show_filds_for(project = None):
    try:
        current_user = frappe.session.user
        hr_manager_roles = ["S - HR Director (Global Admin)", "S - HR L1", "S - HR L2"]
        
        if project and frappe.db.exists("Project", {"name": project, "custom_project_coordinator": current_user}):
            return {"error": 0, "show_fields": 1}
            
        else:
            if any(role in frappe.get_roles(current_user) for role in hr_manager_roles):
                return {"error": 0, "show_fields": 1}                    
        
        return {"error": 0, "show_fields": 0}
    except Exception as e:
        frappe.log_error("error_show_fields_for", frappe.get_traceback())
        return {"error": 1, "message": str(e), "show_fields": 0}
    



