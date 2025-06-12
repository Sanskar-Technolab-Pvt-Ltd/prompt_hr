import frappe

# ! prompt_hr.api.mobile.salary_slip.list
# ? GET SALARY SLIP LIST
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

        # ? GET SALARY SLIP LIST
        salary_slip_list = frappe.get_list(
            "Salary Slip",
            filters=filters,
            or_filters=or_filters,
            fields=frappe.parse_json(fields),
            order_by=order_by,
            limit_page_length=limit_page_length,
            limit_start=limit_start,
        )

    except Exception as e:
        # ? HANDLE ERRORS
        frappe.log_error("Error While Getting Salary Slip List", str(e))
        frappe.clear_messages()
        frappe.local.response["message"] = {
            "success": False,
            "message": f"Error While Getting Salary Slip List: {str(e)}",
            "data": None,
        }

    else:
        # ? HANDLE SUCCESS
        frappe.local.response["message"] = {
            "success": True,
            "message": "Salary Slip List Loaded Successfully!",
            "data": salary_slip_list,
        }
        
        
# ! prompt_hr.api.mobile.salary_slip.get
# ? GET SALARY SLIP DETAIL
@frappe.whitelist()
def get(name):
    try:
        # ? CHECK IF SALARY SLIP  DOC EXISTS OR NOT
        salary_slip_exists = frappe.db.exists("Salary Slip", name)

        # ? IF SALARY SLIP  DOC NOT
        if not salary_slip_exists:
            frappe.throw(
                f"Salary Slip: {name} Does Not Exists!",
                frappe.DoesNotExistError,
            )

        # ? GET SALARY SLIP  DOC
        salary_slip = frappe.get_doc("Salary Slip", name)

    except Exception as e:
        # ? HANDLE ERRORS
        frappe.log_error("Error While Getting Salary Slip Detail", str(e))
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
            "message": "Salary Slip Loaded Successfully!",
            "data": salary_slip,
        }