import frappe


# ! prompt_hr.api.mobile.employee_checkin.list
# ? GET EMPLOYEE CHECKIN LIST
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

        # ? GET EMPLOYEE CHECKIN LIST
        employee_checkin_list = frappe.get_list(
            "Employee Checkin",
            filters=filters,
            or_filters=or_filters,
            fields=frappe.parse_json(fields),
            order_by=order_by,
            limit_page_length=limit_page_length,
            limit_start=limit_start,
        )

    except Exception as e:
        # ? HANDLE ERRORS
        frappe.log_error("Error While Getting Employee Checkin List", str(e))
        frappe.clear_messages()
        frappe.local.response["message"] = {
            "success": False,
            "message": f"Error While Getting Employee Checkin List: {str(e)}",
            "data": None,
        }

    else:
        # ? HANDLE SUCCESS
        frappe.local.response["message"] = {
            "success": True,
            "message": "Employee Checkin List Loaded Successfully!",
            "data": employee_checkin_list,
        }
        


# ! prompt_hr.api.mobile.employee_checkin.get
# ? GET EMPLOYEE CHECKIN   DETAIL
@frappe.whitelist()
def get(name):
    try:
        # ? CHECK IF EMPLOYEE CHECKIN  DOC EXISTS OR NOT
        employee_checkin_exists = frappe.db.exists("Employee Checkin", name)

        # ? IF EMPLOYEE CHECKIN  DOC NOT
        if not employee_checkin_exists:
            frappe.throw(
                f"Employee Checkin: {name} Does Not Exists!",
                frappe.DoesNotExistError,
            )

        # ? GET EMPLOYEE CHECKIN  DOC
        employee_checkin = frappe.get_doc("Employee Checkin", name)

    except Exception as e:
        # ? HANDLE ERRORS
        frappe.log_error("Error While Getting Employee Checkin Detail", str(e))
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
            "message": "Employee Checkin Loaded Successfully!",
            "data": employee_checkin,
        }
        
      
        
# ! prompt_hr.api.mobile.employee_checkin.create
# ? CREATE EMPLOYEE CHECKIN   
   
@frappe.whitelist()
def create(**args):
    try:
        # ? DEFINE MANDATORY FIELDS
        mandatory_fields = {
            "employee": "Employee",
            "log_type": "Log Type",
            

        }

        # ? CHECK IF THE MANDATORY FIELD IS FILLED OR NOT IF NOT THROW ERROR
        for field, field_name in mandatory_fields.items():
            if (
                not args.get(field)
                or args.get(field) == "[]"
                or args.get(field) == "[{}]"
            ):
                frappe.throw(
                    f"Please Fill {field_name} Field!",
                    frappe.MandatoryError,
                )

        # ? IF 'time' NOT PROVIDED, USE CURRENT TIME
        if not args.get("time"):
            args["time"] = frappe.utils.now_datetime()
            
        # ? CREATE EMPLOYEE CHECKIN DOC
        employee_checkin_doc = frappe.get_doc({
            "doctype": "Employee Checkin",
            **args
        })
        employee_checkin_doc.insert()
        frappe.db.commit()

    except Exception as e:
        # ? HANDLE ERRORS
        frappe.log_error("Error While Creating Employee Checkin", str(e))
        frappe.clear_messages()
        frappe.local.response["message"] = {
            "success": False,
            "message": f"Error While Creating Employee Checkin: {str(e)}",
            "data": None,
        }

    else:
        # ? HANDLE SUCCESS
        frappe.local.response["message"] = {
            "success": True,
            "message": "Employee Checkin Created Successfully!",
            "data": employee_checkin_doc,
        }
        