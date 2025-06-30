import frappe


# ! prompt_hr.api.mobile.weekoff_change_request.list
# ? GET WEEKOFF CHANGE REQUEST LIST
@frappe.whitelist()
def list(
    filters=None,
    or_filters=None,
    fields=["name","employee","status"],
    order_by=None,
    limit_page_length=0,
    limit_start=0,
):
    try:

        # ? GET WEEKOFF CHANGE REQUEST LIST
        week_off_request_list = frappe.get_list(
            "WeekOff Change Request",
            filters=filters,
            or_filters=or_filters,
            fields=frappe.parse_json(fields),
            order_by=order_by,
            limit_page_length=limit_page_length,
            limit_start=limit_start,
        )
         # ? FETCH ONLY FIRST IWEEKOFF DETIALS AND SPECIFIC FIELDS
        for req in week_off_request_list:
            req_name = req.get("name")
            if req_name:
                weekoff_details = frappe.get_all(
                    "WeekOff Request Details",
                    filters={"parent": req_name},
                    fields=[
                        "existing_weekoff_date",
                        "existing_weekoff",
                        "new_weekoff_date",
                        "new_weekoff"
                    ],
                    order_by="idx asc" ,
                    limit=1
                )
                
                # Add weekoff_details fields directly to parent if exists
                if weekoff_details:
                    req.update(weekoff_details[0])
                
        
        # ? GET TOTAL COUNT (manually count the names matching filters)
        total_names = frappe.get_list(
            "WeekOff Change Request",
            filters=filters,
            or_filters=or_filters,
            fields=["name"],
            ignore_permissions=False
        )
        total_count = len(total_names)

    except Exception as e:
        # ? HANDLE ERRORS
        frappe.log_error("Error While Getting WeekOff Change Request List", str(e))
        frappe.clear_messages()
        frappe.local.response["message"] = {
            "success": False,
            "message": f"Error While Getting WeekOff Change Request List: {str(e)}",
            "data": None,
        }

    else:
        # ? HANDLE SUCCESS
        frappe.local.response["message"] = {
            "success": True,
            "message": "WeekOff Change Request List Loaded Successfully!",
            "data": week_off_request_list,
            "count": total_count        
        }

# ! prompt_hr.api.mobile.weekoff_change_request.get
# ? GET WEEKOFF CHANGE REQUEST DETAIL
@frappe.whitelist()
def get(name):
    try:
        # ? CHECK IF WEEKOFF CHANGE REQUEST DOC EXISTS OR NOT
        weekoff_change_request_exists = frappe.db.exists("WeekOff Change Request", name)

        # ? IF WEEKOFF CHANGE REQUEST DOC NOT
        if not weekoff_change_request_exists:
            frappe.throw(
                f"WeekOff Change Request: {name} Does Not Exists!",
                frappe.DoesNotExistError,
            )

        # ? GET WEEKOFF CHANGE REQUEST DOC
        weekoff_change_request = frappe.get_doc("WeekOff Change Request", name)

    except Exception as e:
        # ? HANDLE ERRORS
        frappe.log_error("Error While Getting WeekOff Change Request Detail", str(e))
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
            "message": "WeekOff Change Request Loaded Successfully!",
            "data": weekoff_change_request,
        }
        
        

# ! prompt_hr.api.mobile.weekoff_change_request.create
# ? CREATE WEEKOFF CHANGE REQUEST
@frappe.whitelist()
def create(**args):
    try:
        # ? DEFINE MANDATORY FIELDS
        mandatory_fields = {
            "employee": "Employee",
            "weekoff_details": "Weekoff Details"
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
                
        # ? PARSE CHILD TABLE JSON FIELDS
        if args.get("weekoff_details"):
            args["weekoff_details"] = frappe.parse_json(args.get("weekoff_details"))        
                

        # ? CREATE WEEKOFF REQUEST DOC
        weekoff_change_request_doc = frappe.get_doc({
            "doctype": "WeekOff Change Request",
            **args
        })
        weekoff_change_request_doc.insert()
        frappe.db.commit()

    except Exception as e:
        # ? HANDLE ERRORS
        frappe.log_error("Error While Creating WeekOff Change Request", str(e))
        frappe.clear_messages()
        frappe.local.response["message"] = {
            "success": False,
            "message": f"Error While Creating WeekOff Change Request: {str(e)}",
            "data": None,
        }

    else:
        # ? HANDLE SUCCESS
        frappe.local.response["message"] = {
            "success": True,
            "message": "WeekOff Change Request Created Successfully!",
            "data": weekoff_change_request_doc,
        }   
        
# ! prompt_hr.api.mobile.weekoff_change_request.update
# ? UPDATE WEEKOFF CHANGE REQUEST
@frappe.whitelist()
def update(**args):
    try:
        # ? MANDATORY FIELD FOR IDENTIFICATION
        if not args.get("name"):
            frappe.throw("WeekOff Change Request 'name' is required to update the document", frappe.MandatoryError)

        # ? FETCH EXISTING DOC
        weekoff_change_request_doc = frappe.get_doc("WeekOff Change Request", args.get("name"))
        
        # ? PARSE CHILD TABLE JSON FIELDS
        if args.get("weekoff_details"):
            args["weekoff_details"] = frappe.parse_json(args.get("weekoff_details")) 

        # ? UPDATE FIELDS
        for key, value in args.items():
            if key != "name":  # avoid overwriting the document name
                weekoff_change_request_doc.set(key, value)

        weekoff_change_request_doc.save()
        frappe.db.commit()

    except Exception as e:
        # ? HANDLE ERRORS
        frappe.log_error("Error While Updating WeekOff Change Request", str(e))
        frappe.clear_messages()
        frappe.local.response["message"] = {
            "success": False,
            "message": f"Error While Updating WeekOff Change Request: {str(e)}",
            "data": None,
        }

    else:
        # ? HANDLE SUCCESS
        frappe.local.response["message"] = {
            "success": True,
            "message": "WeekOff Change Request Updated Successfully!",
            "data": weekoff_change_request_doc,
        }

# ! prompt_hr.api.mobile.weekoff_change_request.delete
# ? DELETE WEEKOFF CHANGE REQUEST
@frappe.whitelist()
def delete(name=None):
    try:
        # ? CHECK MANDATORY FIELD
        if not name:
            frappe.throw("WeekOff Change Request 'name' is required to delete the document", frappe.MandatoryError)
            
        # ? VERIFY DOCUMENT EXISTS
        if not frappe.db.exists("WeekOff Change Request", name):
            frappe.throw(f"Request with name '{name}' does not exist", frappe.DoesNotExistError)    

        # ? DELETE THE DOCUMENT
        frappe.delete_doc("WeekOff Change Request", name, ignore_permissions=True)
        frappe.db.commit()

    except Exception as e:
        # ? HANDLE ERRORS
        frappe.log_error("Error While Deleting WeekOff Change Request", str(e))
        frappe.clear_messages()
        frappe.local.response["message"] = {
            "success": False,
            "message": f"Error While Deleting WeekOff Change Request: {str(e)}",
            "data": None,
        }

    else:
        # ? HANDLE SUCCESS
        frappe.local.response["message"] = {
            "success": True,
            "message": "WeekOff Change Request Deleted Successfully!",
            "data": {"name": name},
        }