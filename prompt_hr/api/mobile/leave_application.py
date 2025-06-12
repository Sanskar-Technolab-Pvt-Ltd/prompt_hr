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

        # ? GET LEAVE APPLICATION LIST
        leave_application_list = frappe.get_list(
            "Leave Application",
            filters=filters,
            or_filters=or_filters,
            fields=frappe.parse_json(fields),
            order_by=order_by,
            limit_page_length=limit_page_length,    
            limit_start=limit_start,
        )

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
        print(f"\n\n METHOS cALLED\n\n")
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
        attachment_url = None
        if frappe.request.files.get("custom_attachment"):
            file = frappe.request.files["custom_attachment"]
            file_doc = frappe.get_doc({
                "doctype": "File",
                "file_name": file.filename,
                "content": file.read(),
                "is_private": 1,  # Set to private; change to 0 for public
            })
            file_doc.save()
            attachment_url = file_doc.file_url
            
        
        doc_data = args.copy()
        if attachment_url:
            doc_data["custom_attachment"] = attachment_url  # Set custom_attachment field

        
        email_table = frappe.parse_json(doc_data.get("custom_email_cc"))
        doc_data["custom_email_cc"] = email_table
        
        # ? CREATE LEAVE APPLICATION
        leave_application_request_doc = frappe.get_doc({
            "doctype": "Leave Application",
            **doc_data
        })
        
        leave_application_request_doc.insert()
        frappe.db.commit()

        
        # ? ATTACH FILE TO DOCUMENT (IF UPLOADED)
        if attachment_url:
            frappe.get_doc({
                "doctype": "File",
                "file_name": file_doc.file_name,
                "file_url": attachment_url,
                "attached_to_doctype": "Leave Application",
                "attached_to_name": leave_application_request_doc.name,
                "is_private": 1,
            }).insert()
            
        # # ? CREATE LEAVE APPLICATION
        # leave_application_request_doc = frappe.get_doc({
        #     "doctype": "Leave Application",
        #     **args
        # })
        # leave_application_request_doc.insert()
        # frappe.db.commit()
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

        # ? UPDATE FIELDS
        for key, value in args.items():
            if key != "name":  # avoid overwriting the document name
                leave_application_doc.set(key, value)

        leave_application_doc.save()
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
        
        
        
import frappe
 
# ! prompt_hr.api.mobile.salary_slip.get
# ? GET SALARY SLIP DETAIL
@frappe.whitelist()
def gett(name):
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
         