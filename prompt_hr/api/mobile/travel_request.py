import frappe
from frappe.utils.file_manager import save_file

# ! prompt_hr.api.mobile.travel_request.list
# ? GET TRAVEL REQUEST LIST
@frappe.whitelist()
def list(
    filters=None,
    or_filters=None,
    fields=["name","employee","travel_type","purpose_of_travel"],
    order_by=None,
    limit_page_length=0,
    limit_start=0,
):
    try:
        # ? GET Travel Request LIST
        travel_request_list = frappe.get_list(
            "Travel Request",
            filters=filters,
            or_filters=or_filters,
            fields=frappe.parse_json(fields),
            order_by=order_by,
            limit_page_length=limit_page_length,
            limit_start=limit_start,
        )
        
        # ? FETCH ONLY FIRST ITINERARY ITEM AND SPECIFIC FIELDS
        for req in travel_request_list:
            req_name = req.get("name")
            if req_name:
                itinerary = frappe.get_all(
                    "Travel Itinerary",
                    filters={"parent": req_name},
                    fields=[
                        "custom_from_travel",
                        "custom_to_travel",
                        "departure_date",
                        "arrival_date"
                    ],
                    order_by="idx asc" ,
                    limit=1# Only get the first itinerary item
                )
                
                # Add itinerary fields directly to parent if exists
                if itinerary:
                    req.update(itinerary[0])
                
                # Remove the itinerary array since we've moved the fields to parent
                if "itinerary" in req:
                    del req["itinerary"]
        
        # ? GET TOTAL COUNT
        total_names = frappe.get_list(
            "Travel Request",
            filters=filters,
            or_filters=or_filters,
            fields=["name"],
            ignore_permissions=False
        )
        total_count = len(total_names)

    except Exception as e:
        # ? HANDLE ERRORS
        frappe.log_error("Error While Getting Travel Request List", str(e))
        frappe.clear_messages()
        frappe.local.response["message"] = {
            "success": False,
            "message": f"Error While Getting Travel Request List: {str(e)}",
            "data": None,
        }

    else:
        # ? HANDLE SUCCESS
        frappe.local.response["message"] = {
            "success": True,
            "message": "Travel Request List Loaded Successfully!",
            "data": travel_request_list,
            "count": total_count        
        }

# ! prompt_hr.api.mobile.travel_request.get
# ? GET TRAVEL REQUEST DETAIL
@frappe.whitelist()
def get(name):
    try:
        # ? CHECK IF TRAVEL REQUEST DOC EXISTS OR NOT
        travel_request_exists = frappe.db.exists("Travel Request", name)

        # ? IF TRAVEL REQUEST DOC NOT
        if not travel_request_exists:
            frappe.throw(
                f"Travel Request: {name} Does Not Exists!",
                frappe.DoesNotExistError,
            )

        # ? GET TRAVEL REQUEST DOC
        travel_request = frappe.get_doc("Travel Request", name)

    except Exception as e:
        # ? HANDLE ERRORS
        frappe.log_error("Error While Getting Travel Request Detail", str(e))
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
            "message": "Travel Request Loaded Successfully!",
            "data": travel_request,
        }
        
        

# ! prompt_hr.api.mobile.travel_request.create
# ? CREATE TRAVEL REQUEST
@frappe.whitelist()
def create(**args):
    try:
        # ? DEFINE MANDATORY FIELDS
        mandatory_fields = {
            "employee": "Employee",
            "travel_type": "Travel Type",
            "purpose_of_travel": "Purpose of Travel",
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
        if args.get("itinerary"):
            args["itinerary"] = frappe.parse_json(args.get("itinerary"))
            
      
            
        # ? CREATE TRAVEL REQUEST DOC
        travel_request_doc = frappe.get_doc({
            "doctype": "Travel Request",
            **args
        })
        travel_request_doc.insert()
        frappe.db.commit()
        
          # ? HANDLE MULTIPLE FILE UPLOADS
        uploaded_files = frappe.request.files.getlist("file")
        for uploaded_file in uploaded_files:
            save_file(
                uploaded_file.filename,
                uploaded_file.stream.read(),
                "Travel Request",
                travel_request_doc.name,
                is_private=0
            )
        frappe.db.commit()    

    except Exception as e:
        # ? HANDLE ERRORS
        frappe.log_error("Error While Creating Travel Request", str(e))
        frappe.clear_messages()
        frappe.local.response["message"] = {
            "success": False,
            "message": f"Error While Creating Travel Request: {str(e)}",
            "data": None,
        }

    else:
        # ? HANDLE SUCCESS
        frappe.local.response["message"] = {
            "success": True,
            "message": "Travel Request Created Successfully!",
            "data": travel_request_doc,
        }
    

# ! prompt_hr.api.mobile.travel_request.update
# ? UPDATE TRAVEL REQUEST
@frappe.whitelist()
def update(**args):
    try:
        # ? MANDATORY FIELD FOR IDENTIFICATION
        if not args.get("name"):
            frappe.throw("Travel Request 'name' is required to update the document", frappe.MandatoryError)

        # ? FETCH EXISTING DOC
        travel_request_doc = frappe.get_doc("Travel Request", args.get("name"))
        
        # ? PARSE CHILD TABLE JSON FIELDS
        if args.get("itinerary"):
            args["itinerary"] = frappe.parse_json(args.get("itinerary"))

        # ? UPDATE FIELDS
        for key, value in args.items():
            if key != "name":  # avoid overwriting the document name
                travel_request_doc.set(key, value)

        travel_request_doc.save()
        frappe.db.commit()
        
          # ? HANDLE MULTIPLE FILE UPLOADS
        uploaded_files = frappe.request.files.getlist("file")
        for uploaded_file in uploaded_files:
            save_file(
                uploaded_file.filename,
                uploaded_file.stream.read(),
                "Travel Request",
                travel_request_doc.name,
                is_private=0
            )
        frappe.db.commit() 

    except Exception as e:
        # ? HANDLE ERRORS
        frappe.log_error("Error While Updating Travel Request", str(e))
        frappe.clear_messages()
        frappe.local.response["message"] = {
            "success": False,
            "message": f"Error While Updating Travel Request: {str(e)}",
            "data": None,
        }

    else:
        # ? HANDLE SUCCESS
        frappe.local.response["message"] = {
            "success": True,
            "message": "Travel Request Updated Successfully!",
            "data": travel_request_doc,
        }

# ! prompt_hr.api.mobile.travel_request.delete
# ? DELETE TRAVEL REQUEST
@frappe.whitelist()
def delete(name=None):
    try:
        # ? CHECK MANDATORY FIELD
        if not name:
            frappe.throw("Travel Request 'name' is required to delete the document", frappe.MandatoryError)
            
        # ? VERIFY DOCUMENT EXISTS
        if not frappe.db.exists("Travel Request", name):
            frappe.throw(f"Request with name '{name}' does not exist", frappe.DoesNotExistError)       

        # ? DELETE THE DOCUMENT
        frappe.delete_doc("Travel Request", name, ignore_permissions=True)
        frappe.db.commit()

    except Exception as e:
        # ? HANDLE ERRORS
        frappe.log_error("Error While Deleting Travel Request", str(e))
        frappe.clear_messages()
        frappe.local.response["message"] = {
            "success": False,
            "message": f"Error While Deleting Travel Request: {str(e)}",
            "data": None,
        }

    else:
        # ? HANDLE SUCCESS
        frappe.local.response["message"] = {
            "success": True,
            "message": "Travel Request Deleted Successfully!",
            "data": {"name": name},
        }
