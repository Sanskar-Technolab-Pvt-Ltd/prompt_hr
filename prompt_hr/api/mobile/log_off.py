import frappe

# ! prompt_hr.api.mobile.log_off.logout
# ? API FOR LOGOUT AND CLEAR SESSION
@frappe.whitelist(allow_guest=0)
def logout():
    try:
        # ? Get the current session user
        user = frappe.session.user

        # ? Clear session data
        frappe.local.login_manager.logout()
        frappe.db.commit()


    except Exception as e:
        # ? Log error and respond with failure
        frappe.log_error("API Logout Error", str(e))
        frappe.local.response["message"] = {
            "success": False,
            "message": "Logout failed.",
            "data": None,
        }
         # Cleanup extra keys
        frappe.local.response.pop("home_page", None)
        frappe.local.response.pop("full_name", None)
        
        
    else:
        # ? Success response
        frappe.local.response["message"] = {
            "success": True,
            "message": f"User '{user}' logged out successfully.",
            "data": None,
        }    
         # Cleanup extra keys
        frappe.local.response.pop("home_page", None)
        frappe.local.response.pop("full_name", None)