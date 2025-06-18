import frappe
from frappe.utils.file_manager import save_file

# ! prompt_hr.api.mobile.leave_application.list
# ? GET LEAVE APPLICATION REQUEST LIST
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

        current_user = frappe.session.user
        parsed_fields = frappe.parse_json(fields)

        # Ensure required fields are included
        required_fields = ["employee", "owner"]
        for field in required_fields:
            if field not in parsed_fields:
                parsed_fields.append(field)

        # Get current user's employee ID
        current_employee = frappe.get_value("Employee", {"user_id": current_user}, "name")

        # Fetch leave applications
        leave_application_list_raw = frappe.get_list(
            "Leave Application",
            filters=filters,
            or_filters=or_filters,
            fields=parsed_fields,
            order_by=order_by,
            limit_page_length=limit_page_length,
            limit_start=limit_start,
        )

        # Tag each record as Self or Team
        leave_application_list = []
        for entry in leave_application_list_raw:
            if entry.get("employee") == current_employee or entry.get("owner") == current_user:
                entry["request"] = "My Request"
            else:
                entry["request"] = "Team Request"
            leave_application_list.append(entry)

        
        # ? GET TOTAL COUNT (manually count the names matching filters)
        total_names = frappe.get_all(
            "Leave Application",
            filters=filters,
            or_filters=or_filters,
            fields=["name"]
        )
        total_count = len(total_names)
        

    except Exception as e:
        # ? HANDLE ERRORS
        frappe.log_error("Error While Getting Leave Application List", str(e))
        frappe.clear_messages()
        frappe.local.response["message"] = {
            "success": False,
            "message": f"Error While Getting Leave Application List: {str(e)}",
            "data": None,
        }

    else:
        # ? HANDLE SUCCESS
        frappe.local.response["message"] = {
            "success": True,
            "message": "Leave Application List Loaded Successfully!",
            "data": leave_application_list,
            "count": total_count        
        }

# ! prompt_hr.api.mobile.leave_application.get
# ? GET LEAVE APPLICATION DETAIL
@frappe.whitelist()
def get(name):
    try:
        # ? CHECK IF LEAVE APPLICATION DOC EXISTS OR NOT
        leave_application_exists = frappe.db.exists("Leave Application", name)

        # ? IF LEAVE APPLICATION DOC NOT
        if not leave_application_exists:
            frappe.throw(
                f"Leave Application: {name} Does Not Exists!",
                frappe.DoesNotExistError,
            )

        # ? GET LEAVE APPLICATION DOC
        leave_application = frappe.get_doc("Leave Application", name)

    except Exception as e:
        # ? HANDLE ERRORS
        frappe.log_error("Error While Getting Leave Application", str(e))
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
            "message": "Leave Application Loaded Successfully!",
            "data": leave_application,
        }
        
        

# ! prompt_hr.api.mobile.leave_application.create
# ? CREATE LEAVE APPLICATION
@frappe.whitelist()
def create(**args):
    try:
        # ? DEFINE MANDATORY FIELDS
        mandatory_fields = {
            "employee": "Employee",
            "leave_type": "Leave Type",
            "from_date": "From Date",
            "to_date": "To Date",
            "posting_date": "Posting Date",
            "status": "Status"
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
        if args.get("custom_email_cc"):
            args["custom_email_cc"] = frappe.parse_json(args.get("custom_email_cc"))
            
        # ? CREATE LEAVE APPLICATION
        leave_application_request_doc = frappe.get_doc({
            "doctype": "Leave Application",
            **args
        })
        
        leave_application_request_doc.insert()
        frappe.db.commit()
        
        # ? HANDLE MULTIPLE FILE UPLOADS
        uploaded_files = frappe.request.files.getlist("file")
        for uploaded_file in uploaded_files:
            save_file(
                uploaded_file.filename,
                uploaded_file.stream.read(),
                "Leave Application",
                leave_application_request_doc.name,
                is_private=0
            )
        frappe.db.commit()

    except Exception as e:
        # ? HANDLE ERRORS
        frappe.log_error("Error While Creating Leave Application", str(e))
        frappe.clear_messages()
        frappe.local.response["message"] = {
            "success": False,
            "message": f"Error While Creating Leave Application: {str(e)}",
            "data": None,
        }

    else:
        # ? HANDLE SUCCESS
        frappe.local.response["message"] = {
            "success": True,
            "message": "Leave Application Created Successfully!",
            "data": leave_application_request_doc,
        }   
        
# ! prompt_hr.api.mobile.leave_application.update
# ? UPDATE LEAVE APPLICATION REQUEST
@frappe.whitelist()
def update(**args):
    try:
        # ? MANDATORY FIELD FOR IDENTIFICATION
        if not args.get("name"):
            frappe.throw("Leave Application 'name' is required to update the document", frappe.MandatoryError)

        # ? FETCH EXISTING DOC
        leave_application_doc = frappe.get_doc("Leave Application", args.get("name"))
        
        # ? PARSE CHILD TABLE JSON FIELDS
        if args.get("custom_email_cc"):
            args["custom_email_cc"] = frappe.parse_json(args.get("custom_email_cc"))

        # ? UPDATE FIELDS
        for key, value in args.items():
            if key != "name":  # avoid overwriting the document name
                leave_application_doc.set(key, value)

        leave_application_doc.save()
        frappe.db.commit()
        
        # ? HANDLE MULTIPLE FILE UPLOADS
        uploaded_files = frappe.request.files.getlist("file")
        for uploaded_file in uploaded_files:
            save_file(
                uploaded_file.filename,
                uploaded_file.stream.read(),
                "Leave Application",
                leave_application_doc.name,
                is_private=0
            )
        frappe.db.commit()

    except Exception as e:
        # ? HANDLE ERRORS
        frappe.log_error("Error While Updating Leave Application", str(e))
        frappe.clear_messages()
        frappe.local.response["message"] = {
            "success": False,
            "message": f"Error While Updating Leave Application: {str(e)}",
            "data": None,
        }

    else:
        # ? HANDLE SUCCESS
        frappe.local.response["message"] = {
            "success": True,
            "message": "Leave Application Updated Successfully!",
            "data": leave_application_doc,
        }

# ! prompt_hr.api.mobile.leave_application.delete
# ? DELETE LEAVE APPLICATION
@frappe.whitelist()
def delete(name=None):
    try:
        # ? CHECK MANDATORY FIELD
        if not name:
            frappe.throw("Leave Application 'name' is required to delete the document", frappe.MandatoryError)
            
        # ? VERIFY DOCUMENT EXISTS
        if not frappe.db.exists("Leave Application", name):
            frappe.throw(f"Request with name '{name}' does not exist", frappe.DoesNotExistError)    

        # ? DELETE THE DOCUMENT
        frappe.delete_doc("Leave Application", name, ignore_permissions=True)
        frappe.db.commit()

    except Exception as e:
        # ? HANDLE ERRORS
        frappe.log_error("Error While Deleting Leave Application", str(e))
        frappe.clear_messages()
        frappe.local.response["message"] = {
            "success": False,
            "message": f"Error While Deleting Leave Application: {str(e)}",
            "data": None,
        }

    else:
        # ? HANDLE SUCCESS
        frappe.local.response["message"] = {
            "success": True,
            "message": "Leave Application Deleted Successfully!",
            "data": {"name": name},
        }
        
        
        
