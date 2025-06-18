import frappe

# ! prompt_hr.api.mobile.notification_log.list
# ? GET NOTIFICATION_LOG LIST
@frappe.whitelist()
def list(
    filters=None,
    or_filters=None,
    fields=["*"],
    order_by=None,
    limit_page_length=0,
    limit_start=0,
):
    try:

        # ? GET NOTIFICATION_LOG LIST
        notification_log_list = frappe.get_list(
            "Notification Log",
            filters=filters,
            or_filters=or_filters,
            fields=frappe.parse_json(fields),
            order_by=order_by,
            limit_page_length=limit_page_length,
            limit_start=limit_start,
        )
        
        # ? GET TOTAL COUNT (manually count the names matching filters)
        total_names = frappe.get_all(
            "Notification Log",
            filters=filters,
            or_filters=or_filters,
            fields=["name"]
        )
        total_count = len(total_names)

    except Exception as e:
        # ? HANDLE ERRORS
        frappe.log_error("Error While Getting Notification Log List", str(e))
        frappe.clear_messages()
        frappe.local.response["message"] = {
            "success": False,
            "message": f"Error While Getting Notification Log List: {str(e)}",
            "data": None,
        }
        
        

    else:
        # ? HANDLE SUCCESS
        frappe.local.response["message"] = {
            "success": True,
            "message": "Notification Log List Loaded Successfully!",
            "data": notification_log_list,
            "count": total_count        
        }
          
# ! prompt_hr.api.mobile.notification_log.get
# ? GET NOTIFICATION_LOG DETAIL
@frappe.whitelist()
def get(name):
    try:
        # ? CHECK IF NOTIFICATION_LOG  DOC EXISTS OR NOT
        notification_log_exists = frappe.db.exists("Notification Log", name)

        # ? IF NOTIFICATION_LOG  DOC NOT
        if not notification_log_exists:
            frappe.throw(
                f"Notification Log: {name} Does Not Exists!",
                frappe.DoesNotExistError,
            )

        # ? GET NOTIFICATION_LOG  DOC
        notification_log = frappe.get_doc("Notification Log", name)
        
        

    except Exception as e:
        # ? HANDLE ERRORS
        frappe.log_error("Error While Getting Notification Log Detail", str(e))
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
            "message": "Notification Log Loaded Successfully!",
            "data": notification_log,
        }