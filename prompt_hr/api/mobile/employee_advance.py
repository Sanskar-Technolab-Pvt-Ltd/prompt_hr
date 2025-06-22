import frappe
from frappe.utils.file_manager import save_file

# Employee Advance
# EMPLOYEE ADVANCE
# employee_advance

# ! prompt_hr.api.mobile.employee_advance.list
# ? GET EMPLOYEE ADVANCE LIST
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

        # ? GET EMPLOYEE ADVANCE LIST
        employee_advance_list = frappe.get_list(
            "Employee Advance",
            filters=filters,
            or_filters=or_filters,
            fields=frappe.parse_json(fields),
            order_by=order_by,
            limit_page_length=limit_page_length,
            limit_start=limit_start,
        )
        
        # ? GET TOTAL COUNT (manually count the names matching filters)
        total_names = frappe.get_all(
            "Employee Advance",
            filters=filters,
            or_filters=or_filters,
            fields=["name"]
        )
        total_count = len(total_names)
        

    except Exception as e:
        # ? HANDLE ERRORS
        frappe.log_error("Error While Getting Employee Advance List", str(e))
        frappe.clear_messages()
        frappe.local.response["message"] = {
            "success": False,
            "message": f"Error While Getting Employee Advance List: {str(e)}",
            "data": None,
        }

    else:
        # ? HANDLE SUCCESS
        frappe.local.response["message"] = {
            "success": True,
            "message": "Employee Advance List Loaded Successfully!",
            "data": employee_advance_list,
            "count": total_count              
        }
        




# ! prompt_hr.api.mobile.employee_advance.get
# ? GET EMPLOYEE ADVANCE DETAIL
@frappe.whitelist()
def get(name):
    try:
        # ? CHECK IF EMPLOYEE ADVANCE  DOC EXISTS OR NOT
        employee_advance_exists = frappe.db.exists("Employee Advance", name)

        # ? IF EMPLOYEE ADVANCE  DOC NOT
        if not employee_advance_exists:
            frappe.throw(
                f"Employee Advance: {name} Does Not Exists!",
                frappe.DoesNotExistError,
            )

        # ? GET EMPLOYEE ADVANCE  DOC
        employee_advance = frappe.get_doc("Employee Advance", name)

    except Exception as e:
        # ? HANDLE ERRORS
        frappe.log_error("Error While Getting Employee Advance Detail", str(e))
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
            "message": "Employee Advance Loaded Successfully!",
            "data": employee_advance,
        }
        
      
# ! prompt_hr.api.mobile.employee_advance.create
# ? CREATE EMPLOYEE ADVANCE WITH OPTIONAL FILE ATTACHMENT

@frappe.whitelist()
def create(**args):
    try:
        # ? DEFINE MANDATORY FIELDS
        mandatory_fields = {
            "employee": "Employee",
            "posting_date": "Posting Date",
            # "currency": "Currency",
            "purpose": "Purpose",
            "advance_amount": "Advance Amount"
        }

        # ? VALIDATE MANDATORY FIELDS
        for field, field_name in mandatory_fields.items():
            if (
                not args.get(field)
                or args.get(field) == "[]"
                or args.get(field) == "[{}]"
            ):
                frappe.throw(f"Please Fill {field_name} Field!", frappe.MandatoryError)

        # ? FETCH GLOBAL DEFAULT CURRENCY IF NOT PROVIDED
        currency = args.get("currency") or frappe.db.get_single_value("Global Defaults", "default_currency")
        args["currency"] = currency
        args["exchange_rate"] = 1.0

        # ? CREATE EMPLOYEE ADVANCE DOC
        employee_advance_doc = frappe.get_doc({
            "doctype": "Employee Advance",
            **args
        })

        # ? CREATE EMPLOYEE ADVANCE DOC
        employee_advance_doc = frappe.get_doc({
            "doctype": "Employee Advance",
            **args
        })
        employee_advance_doc.insert()
        frappe.db.commit()

        # ? HANDLE MULTIPLE FILE UPLOADS
        uploaded_files = frappe.request.files.getlist("file")
        for uploaded_file in uploaded_files:
            save_file(
                uploaded_file.filename,
                uploaded_file.stream.read(),
                "Employee Advance",
                employee_advance_doc.name,
                is_private=0
            )
        frappe.db.commit()

    except Exception as e:
        frappe.log_error("Error While Creating Employee Advance", str(e))
        frappe.clear_messages()
        frappe.local.response["message"] = {
            "success": False,
            "message": f"Error While Creating Employee Advance: {str(e)}",
            "data": None,
        }

    else:
        frappe.local.response["message"] = {
            "success": True,
            "message": "Employee Advance Created Successfully!",
            "data": employee_advance_doc,
        }
         
         
# ! prompt_hr.api.mobile.employee_advance.update
# ? UPDATE EMPLOYEE ADVANCE

@frappe.whitelist()
def update(**args):
    try:
        # ? MANDATORY FIELD FOR IDENTIFICATION
        if not args.get("name"):
            frappe.throw("Employee Advance 'name' is required to update the document", frappe.MandatoryError)

        # ? FETCH EXISTING DOC
        employee_advance_doc = frappe.get_doc("Employee Advance", args.get("name"))

        # ? UPDATE FIELDS
        for key, value in args.items():
            if key != "name":  # avoid overwriting the document name
                employee_advance_doc.set(key, value)

        employee_advance_doc.save()
        frappe.db.commit()
        
        # ? HANDLE MULTIPLE FILE UPLOADS
        uploaded_files = frappe.request.files.getlist("file")
        for uploaded_file in uploaded_files:
            save_file(
                uploaded_file.filename,
                uploaded_file.stream.read(),
                "Employee Advance",
                employee_advance_doc.name,
                is_private=0
            )
        frappe.db.commit()


    except Exception as e:
        # ? HANDLE ERRORS
        frappe.log_error("Error While Updating Employee Advance", str(e))
        frappe.clear_messages()
        frappe.local.response["message"] = {
            "success": False,
            "message": f"Error While Updating Employee Advance: {str(e)}",
            "data": None,
        }

    else:
        # ? HANDLE SUCCESS
        frappe.local.response["message"] = {
            "success": True,
            "message": "Employee Advance Updated Successfully!",
            "data": employee_advance_doc,
        }




# ! prompt_hr.api.mobile.employee_advance.delete
# ? DELETE EMPLOYEE ADVANCE

@frappe.whitelist()
def delete(name=None):
    try:
        # ? CHECK MANDATORY FIELD
        if not name:
            frappe.throw("Employee Advance 'name' is required to delete the document", frappe.MandatoryError)
            
        # ? VERIFY DOCUMENT EXISTS
        if not frappe.db.exists("Employee Advance", name):
            frappe.throw(f"Request with name '{name}' does not exist", frappe.DoesNotExistError)     

        # ? DELETE THE DOCUMENT
        frappe.delete_doc("Employee Advance", name, ignore_permissions=True)
        frappe.db.commit()

    except Exception as e:
        # ? HANDLE ERRORS
        frappe.log_error("Error While Deleting Employee Advance", str(e))
        frappe.clear_messages()
        frappe.local.response["message"] = {
            "success": False,
            "message": f"Error While Deleting Employee Advance: {str(e)}",
            "data": None,
        }

    else:
        # ? HANDLE SUCCESS
        frappe.local.response["message"] = {
            "success": True,
            "message": "Employee Advance Deleted Successfully!",
            "data": {"name": name},
        }


# ! prompt_hr.api.mobile.employee_advance.mode_of_payment_list
# ? GET MODE OF PAYMENT LIST
@frappe.whitelist()
def mode_of_payment_list(
    filters=None,
    or_filters=None,
    fields=["*"],
    order_by=None,
    limit_page_length=0,
    limit_start=0,
):
    try:

        # ? GET MODE OF PAYMENT LIST
        mode_of_payment_list = frappe.get_list(
            "Mode of Payment",
            filters=filters,
            or_filters=or_filters,
            fields=frappe.parse_json(fields),
            order_by=order_by,
            limit_page_length=limit_page_length,
            limit_start=limit_start,
        )
        
        # ? GET TOTAL COUNT (manually count the names matching filters)
        total_names = frappe.get_all(
            "Mode of Payment",
            filters=filters,
            or_filters=or_filters,
            fields=["name"]
        )
        total_count = len(total_names)
        

    except Exception as e:
        # ? HANDLE ERRORS
        frappe.log_error("Error While Getting Mode of Payment List", str(e))
        frappe.clear_messages()
        frappe.local.response["message"] = {
            "success": False,
            "message": f"Error While Getting Mode of Payment List: {str(e)}",
            "data": None,
        }

    else:
        # ? HANDLE SUCCESS
        frappe.local.response["message"] = {
            "success": True,
            "message": "Mode of Payment List Loaded Successfully!",
            "data": mode_of_payment_list,
            "count": total_count              
        }
        
         