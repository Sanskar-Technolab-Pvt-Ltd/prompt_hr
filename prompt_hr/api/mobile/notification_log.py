import frappe
import json

def safe_parse_json(data):
    if not data:
        return {}
    if isinstance(data, dict):
        return data
    try:
        return frappe.parse_json(data)
    except Exception:
        return {}


# ! prompt_hr.api.mobile.notification_log.list
# ? GET NOTIFICATION_LOG LIST
@frappe.whitelist()
def list(
    filters=None,
    or_filters=None,
    fields="[*]",
    order_by=None,
    limit_page_length=0,
    limit_start=0,
):
    try:
        filters = safe_parse_json(filters)
        or_filters = safe_parse_json(or_filters)
        fields = safe_parse_json(fields) or ["*"]

        # ? GET NOTIFICATION_LOG LIST
        notification_log_list = frappe.get_all(
            "Notification Log",
            filters=filters,
            or_filters=or_filters,
            fields=fields,
            order_by=order_by,
            limit_page_length=limit_page_length,
            limit_start=limit_start,
        )

        # Read count
        read_filters = filters.copy()
        read_filters['read'] = 1
        read_count = frappe.db.count("Notification Log", filters=read_filters)

        # Unread count
        unread_filters = filters.copy()
        unread_filters['read'] = 0
        unread_count = frappe.db.count("Notification Log", filters=unread_filters)

        total_count = int(read_count or 0) + int(unread_count or 0)

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
            "count": total_count,
            "read_count": read_count,
            "unread_count": unread_count
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
        frappe.db.set_value(
            "Notification Log",
            {"name": name, "read": 0},
            "read",
            1,
        )
        # ? COMMIT CHANGES
        frappe.db.commit()
        

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
        
# ! prompt_hr.api.mobile.notification_log.mark_all_as_read  
@frappe.whitelist()
def mark_all_as_read(user):
    try:
        # ? MARK ALL NOTIFICATIONS AS READ FOR THE USER
        frappe.db.set_value(
            "Notification Log",
            {"for_user": user, "read": 0},
            "read",
            1,
        )

        # ? COMMIT CHANGES
        frappe.db.commit()

    except Exception as e:
        # ? HANDLE ERRORS
        frappe.log_error("Error While Marking All Notifications as Read", str(e))
        frappe.clear_messages()
        frappe.local.response["message"] = {
            "success": False,
            "message": f"Error While Marking All Notifications as Read: {str(e)}",
            "data": None,
        }
    else:
        # ? HANDLE SUCCESS
        frappe.local.response["message"] = {
            "success": True,
            "message": "All Notifications Marked as Read Successfully!",
            "data": None,
        }