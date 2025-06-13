import frappe


# ! prompt_hr.api.mobile.attendance_request.list
# ? GET ATTENDANCE REQUEST LIST
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

        # ? GET ATTENDANCE REQUEST LIST
        attendance_request_list = frappe.get_list(
            "Attendance Request",
            filters=filters,
            or_filters=or_filters,
            fields=frappe.parse_json(fields),
            order_by=order_by,
            limit_page_length=limit_page_length,
            limit_start=limit_start,
        )

    except Exception as e:
        # ? HANDLE ERRORS
        frappe.log_error("Error While Getting Attendance Request List", str(e))
        frappe.clear_messages()
        frappe.local.response["message"] = {
            "success": False,
            "message": f"Error While Getting Attendance Request List: {str(e)}",
            "data": None,
        }

    else:
        # ? HANDLE SUCCESS
        frappe.local.response["message"] = {
            "success": True,
            "message": "Attendance Request List Loaded Successfully!",
            "data": attendance_request_list,
        }
        




# ! prompt_hr.api.mobile.attendance_request.get
# ? GET ATTENDANCE REQUEST DETAIL
@frappe.whitelist()
def get(name):
    try:
        # ? CHECK IF ATTENDANCE REQUEST  DOC EXISTS OR NOT
        attendance_request_exists = frappe.db.exists("Attendance Request", name)

        # ? IF ATTENDANCE REQUEST  DOC NOT
        if not attendance_request_exists:
            frappe.throw(
                f"Attendance Request: {name} Does Not Exists!",
                frappe.DoesNotExistError,
            )

        # ? GET ATTENDANCE REQUEST  DOC
        attendance_request = frappe.get_doc("Attendance Request", name)

    except Exception as e:
        # ? HANDLE ERRORS
        frappe.log_error("Error While Getting Attendance Request Detail", str(e))
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
            "message": "Attendance Request Loaded Successfully!",
            "data": attendance_request,
        }
        
      


# ! prompt_hr.api.mobile.attendance_request.create
# ? CREATE ATTENDANCE REQUEST   
   
@frappe.whitelist()
def create(**args):
    try:
        # ? DEFINE MANDATORY FIELDS
        mandatory_fields = {
            "employee": "Employee",
            "from_date": "From Date",
            "to_date": "To Date",
            "reason": "Reason"
            

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

            
        # ? CREATE ATTENDANCE REQUEST DOC
        attendance_request_doc = frappe.get_doc({
            "doctype": "Attendance Request",
            **args
        })
        attendance_request_doc.insert()
        frappe.db.commit()

    except Exception as e:
        # ? HANDLE ERRORS
        frappe.log_error("Error While Creating Attendance Request", str(e))
        frappe.clear_messages()
        frappe.local.response["message"] = {
            "success": False,
            "message": f"Error While Creating Attendance Request: {str(e)}",
            "data": None,
        }

    else:
        # ? HANDLE SUCCESS
        frappe.local.response["message"] = {
            "success": True,
            "message": "Attendance Request Created Successfully!",
            "data": attendance_request_doc,
        }
         
         
# ! prompt_hr.api.mobile.attendance_request.update
# ? UPDATE ATTENDANCE REQUEST

@frappe.whitelist()
def update(**args):
    try:
        # ? MANDATORY FIELD FOR IDENTIFICATION
        if not args.get("name"):
            frappe.throw("Attendance Request 'name' is required to update the document", frappe.MandatoryError)

        # ? FETCH EXISTING DOC
        attendance_request_doc = frappe.get_doc("Attendance Request", args.get("name"))

        # ? UPDATE FIELDS
        for key, value in args.items():
            if key != "name":  # avoid overwriting the document name
                attendance_request_doc.set(key, value)

        attendance_request_doc.save()
        frappe.db.commit()

    except Exception as e:
        # ? HANDLE ERRORS
        frappe.log_error("Error While Updating Attendance Request", str(e))
        frappe.clear_messages()
        frappe.local.response["message"] = {
            "success": False,
            "message": f"Error While Updating Attendance Request: {str(e)}",
            "data": None,
        }

    else:
        # ? HANDLE SUCCESS
        frappe.local.response["message"] = {
            "success": True,
            "message": "Attendance Request Updated Successfully!",
            "data": attendance_request_doc,
        }




# ! prompt_hr.api.mobile.attendance_request.delete
# ? DELETE ATTENDANCE REQUEST

@frappe.whitelist()
def delete(name=None):
    try:
        # ? CHECK MANDATORY FIELD
        if not name:
            frappe.throw("Attendance Request 'name' is required to delete the document", frappe.MandatoryError)
            
        # ? VERIFY DOCUMENT EXISTS
        if not frappe.db.exists("Attendance Request", name):
            frappe.throw(f"Request with name '{name}' does not exist", frappe.DoesNotExistError)        

        # ? DELETE THE DOCUMENT
        frappe.delete_doc("Attendance Request", name, ignore_permissions=True)
        frappe.db.commit()

    except Exception as e:
        # ? HANDLE ERRORS
        frappe.log_error("Error While Deleting Attendance Request", str(e))
        frappe.clear_messages()
        frappe.local.response["message"] = {
            "success": False,
            "message": f"Error While Deleting Attendance Request: {str(e)}",
            "data": None,
        }

    else:
        # ? HANDLE SUCCESS
        frappe.local.response["message"] = {
            "success": True,
            "message": "Attendance Request Deleted Successfully!",
            "data": {"name": name},
        }
         