import frappe


# ! prompt_hr.api.mobile.shift_request.list
# ? GET SHIFT REQUEST LIST
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

        # ? GET SHIFT REQUEST LIST
        shift_request_list = frappe.get_list(
            "Shift Request",
            filters=filters,
            or_filters=or_filters,
            fields=frappe.parse_json(fields),
            order_by=order_by,
            limit_page_length=limit_page_length,
            limit_start=limit_start,
        )

    except Exception as e:
        # ? HANDLE ERRORS
        frappe.log_error("Error While Getting Shift Request List", str(e))
        frappe.clear_messages()
        frappe.local.response["message"] = {
            "success": False,
            "message": f"Error While Getting Shift Request List: {str(e)}",
            "data": None,
        }

    else:
        # ? HANDLE SUCCESS
        frappe.local.response["message"] = {
            "success": True,
            "message": "Shift Request List Loaded Successfully!",
            "data": shift_request_list,
        }
        


# shift_request
# SHIFT REQUEST
# Shift Request


# ! prompt_hr.api.mobile.shift_request.get
# ? GET SHIFT REQUEST DETAIL
@frappe.whitelist()
def get(name):
    try:
        # ? CHECK IF EMPLOYEE CHECKIN  DOC EXISTS OR NOT
        shift_request_exists = frappe.db.exists("Shift Request", name)

        # ? IF EMPLOYEE CHECKIN  DOC NOT
        if not shift_request_exists:
            frappe.throw(
                f"Shift Request: {name} Does Not Exists!",
                frappe.DoesNotExistError,
            )

        # ? GET EMPLOYEE CHECKIN  DOC
        shift_request = frappe.get_doc("Shift Request", name)

    except Exception as e:
        # ? HANDLE ERRORS
        frappe.log_error("Error While Getting Shift Request Detail", str(e))
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
            "message": "Shift Request Loaded Successfully!",
            "data": shift_request,
        }
        
      
 