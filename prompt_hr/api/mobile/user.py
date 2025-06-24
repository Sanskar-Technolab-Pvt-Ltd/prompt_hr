import frappe
# ! prompt_hr.api.mobile.user.list
@frappe.whitelist()
def list(
    filters=None,
    or_filters=None,
    fields=["name"],
    order_by=None,
    limit_page_length=0,
    limit_start=0,
):
    try:

        user_list = frappe.get_list(
            "User",
            filters=filters,
            or_filters=or_filters,
            fields=frappe.parse_json(fields),
            order_by=order_by,
            limit_page_length=limit_page_length,
            limit_start=limit_start,
        )
        
        # ? GET TOTAL COUNT (manually count the names matching filters)
        total_names = frappe.get_list(
            "User",
            filters=filters,
            or_filters=or_filters,
            fields=["name"],
            ignore_permissions=False
        )
        total_count = len(total_names)
        
    except Exception as e:
        # ? HANDLE ERRORS
        frappe.log_error("Error While Getting User List", str(e))
        frappe.clear_messages()
        frappe.local.response["message"] = {
            "success": False,
            "message": f"Error While Getting User List: {str(e)}",
            "data": None,
        }

    else:
        # ? HANDLE SUCCESS
        frappe.local.response["message"] = {
            "success": True,
            "message": "User List Loaded Successfully!",
            "data": user_list,
            "count": total_count        
        }
        