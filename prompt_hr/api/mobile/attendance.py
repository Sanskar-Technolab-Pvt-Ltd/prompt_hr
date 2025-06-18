import frappe

# ! prompt_hr.api.mobile.attendance.list
# ? GET ATTENDANCE LIST
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

        # ? GET ATTENDANCE LIST
        attendance_list = frappe.get_list(
            "Attendance",
            filters=filters,
            or_filters=or_filters,
            fields=frappe.parse_json(fields),
            order_by=order_by,
            limit_page_length=limit_page_length,
            limit_start=limit_start,
        )
        
        # ? GET TOTAL COUNT (manually count the names matching filters)
        total_names = frappe.get_all(
            "Attendance",
            filters=filters,
            or_filters=or_filters,
            fields=["name"]
        )
        
        total_count = len(total_names)
        
    except Exception as e:
        # ? HANDLE ERRORS
        frappe.log_error("Error While Getting Attendance List", str(e))
        frappe.clear_messages()
        frappe.local.response["message"] = {
            "success": False,
            "message": f"Error While Getting Attendance List: {str(e)}",
            "data": None,
        }

    else:
        # ? HANDLE SUCCESS
        frappe.local.response["message"] = {
            "success": True,
            "message": "Attendance List Loaded Successfully!",
            "data": attendance_list,
            "count": total_count        
        }
          
# ! prompt_hr.api.mobile.attendance.get
# ? GET ATTENDANCE DETAIL
@frappe.whitelist()
def get(name):
    try:
        # ? CHECK IF ATTENDANCE  DOC EXISTS OR NOT
        attendance_exists = frappe.db.exists("Attendance", name)

        # ? IF ATTENDANCE  DOC NOT
        if not attendance_exists:
            frappe.throw(
                f"Attendance: {name} Does Not Exists!",
                frappe.DoesNotExistError,
            )

        # ? GET ATTENDANCE  DOC
        attendance = frappe.get_doc("Attendance", name)

    except Exception as e:
        # ? HANDLE ERRORS
        frappe.log_error("Error While Getting Attendance Detail", str(e))
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
            "message": "Attendance Loaded Successfully!",
            "data": attendance,
        }