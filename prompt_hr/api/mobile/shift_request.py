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
        




# ! prompt_hr.api.mobile.shift_request.get
# ? GET SHIFT REQUEST DETAIL
@frappe.whitelist()
def get(name):
    try:
        # ? CHECK IF SHIFT REQUEST  DOC EXISTS OR NOT
        shift_request_exists = frappe.db.exists("Shift Request", name)

        # ? IF SHIFT REQUEST  DOC NOT
        if not shift_request_exists:
            frappe.throw(
                f"Shift Request: {name} Does Not Exists!",
                frappe.DoesNotExistError,
            )

        # ? GET SHIFT REQUEST  DOC
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
        
      


# ! prompt_hr.api.mobile.shift_request.create
# ? CREATE SHIFT REQUEST   
   
@frappe.whitelist()
def create(**args):
    try:
        # ? DEFINE MANDATORY FIELDS
        mandatory_fields = {
            "employee": "Employee",
            "shift_type": "Shift Type",
            "from_date": "From Date",
            "to_date": "To Date",
            "approver": "Approver"
            

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

            
        # ? CREATE SHIFT REQUEST DOC
        shift_request_doc = frappe.get_doc({
            "doctype": "Shift Request",
            **args
        })
        shift_request_doc.insert()
        frappe.db.commit()

    except Exception as e:
        # ? HANDLE ERRORS
        frappe.log_error("Error While Creating Shift Request", str(e))
        frappe.clear_messages()
        frappe.local.response["message"] = {
            "success": False,
            "message": f"Error While Creating Shift Request: {str(e)}",
            "data": None,
        }

    else:
        # ? HANDLE SUCCESS
        frappe.local.response["message"] = {
            "success": True,
            "message": "Shift Request Created Successfully!",
            "data": shift_request_doc,
        }
         
         
# ! prompt_hr.api.mobile.shift_request.update
# ? UPDATE SHIFT REQUEST

@frappe.whitelist()
def update(**args):
    try:
        # ? MANDATORY FIELD FOR IDENTIFICATION
        if not args.get("name"):
            frappe.throw("Shift Request 'name' is required to update the document", frappe.MandatoryError)

        # ? FETCH EXISTING DOC
        shift_request_doc = frappe.get_doc("Shift Request", args.get("name"))

        # ? UPDATE FIELDS
        for key, value in args.items():
            if key != "name":  # avoid overwriting the document name
                shift_request_doc.set(key, value)

        shift_request_doc.save()
        frappe.db.commit()

    except Exception as e:
        # ? HANDLE ERRORS
        frappe.log_error("Error While Updating Shift Request", str(e))
        frappe.clear_messages()
        frappe.local.response["message"] = {
            "success": False,
            "message": f"Error While Updating Shift Request: {str(e)}",
            "data": None,
        }

    else:
        # ? HANDLE SUCCESS
        frappe.local.response["message"] = {
            "success": True,
            "message": "Shift Request Updated Successfully!",
            "data": shift_request_doc,
        }




# ! prompt_hr.api.mobile.shift_request.delete
# ? DELETE SHIFT REQUEST

@frappe.whitelist()
def delete(name=None):
    try:
        # ? CHECK MANDATORY FIELD
        if not name:
            frappe.throw("Shift Request 'name' is required to delete the document", frappe.MandatoryError)

        # ? DELETE THE DOCUMENT
        frappe.delete_doc("Shift Request", name, ignore_permissions=True)
        frappe.db.commit()

    except Exception as e:
        # ? HANDLE ERRORS
        frappe.log_error("Error While Deleting Shift Request", str(e))
        frappe.clear_messages()
        frappe.local.response["message"] = {
            "success": False,
            "message": f"Error While Deleting Shift Request: {str(e)}",
            "data": None,
        }

    else:
        # ? HANDLE SUCCESS
        frappe.local.response["message"] = {
            "success": True,
            "message": "Shift Request Deleted Successfully!",
            "data": {"name": name},
        }
         