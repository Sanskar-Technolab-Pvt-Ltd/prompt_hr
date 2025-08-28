
import frappe

@frappe.whitelist()
def get(doctype):
    try:
        if not doctype:
            frappe.throw("doctype is required", frappe.MandatoryError)

        status = ["Open","Draft","Approved","Rejected"]

    except Exception as e:
        # ? HANDLE ERRORS
        frappe.log_error("Error While Getting Status", str(e))
        frappe.clear_messages()
        frappe.local.response["message"] = {
            "success": False,
            "message": str(e),
            "data": None,
        }

    else:
        # ? HANDLE SUCCESS
        frappe.local.response["message"] = {
            "success": True,
            "message": "Status Loaded Successfully!",
            "data": status,
        }