import frappe
from frappe.utils.file_manager import save_file
from prompt_hr.py.utils import is_user_reporting_manager_or_hr


# ! prompt_hr.api.mobile.attendance_regularization.list
# ? GET Attendance Regularization LIST
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
        # ? GET Attendance Regularization List
        attendance_regularization_list = frappe.get_list(
            "Attendance Regularization",
            filters=filters,
            or_filters=or_filters,
            fields=frappe.parse_json(fields),
            order_by=order_by,
            limit_page_length=limit_page_length,
            limit_start=limit_start,
        )
        
        for attendance in attendance_regularization_list:            
            attendance['status'] = attendance['workflow_state']
        
        total_count = len(attendance_regularization_list)

    except Exception as e:
        # ? HANDLE ERRORS
        frappe.log_error("Error While Getting Attendance Regularization List", str(e))
        frappe.clear_messages()
        frappe.local.response["message"] = {
            "success": False,
            "message": f"While Getting Attendance Regularization List: {str(e)}",
            "data": None,
        }

    else:
        # ? HANDLE SUCCESS
        frappe.local.response["message"] = {
            "success": True,
            "message": "Attendance Regularization List Loaded Successfully!",
            "data": attendance_regularization_list,
            "count": total_count        
        }

# ! prompt_hr.api.mobile.attendance_regularization.get
# ? GET ATTENDANCE REGULARIZATION DETAIL
@frappe.whitelist()
def get(name):
    try: 
        # ? CHECK IF ATTENDANCE REGULARIZATION DOC EXISTS OR NOT
        attendance_regularization_exists = frappe.db.exists("Attendance Regularization", name)
        
        # ? IF ATTENDANCE REGULARIZATION DOC NOT
        if not attendance_regularization_exists:
            frappe.throw(
                f"Attendance Regularization: {name} Does Not Exists!",
                frappe.DoesNotExistError,
            )

        # ? GET ATTENDANCE REGULARIZATION DOC
        attendance_regularization = frappe.get_doc("Attendance Regularization", name)
        attendance_regularization.status = attendance_regularization.workflow_state
        # attendance_regularization.status = "Rejected"
    except Exception as e:
        # ? HANDLE ERRORS
        frappe.log_error("While Getting Attendance Regularization Detail", str(e))
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
            "message": "Attendance Regularization Loaded Successfully!",
            "data": attendance_regularization,
        }
        
        

# ! prompt_hr.api.mobile.attendance_regularization.create  
# ? CREATE ATTENDANCE REGULARIZATION
@frappe.whitelist()
def create(**args):
    try:
        # ? DEFINE MANDATORY FIELDS
        mandatory_fields = {
            "employee": "Employee",
            "regularization_date": "Regularization Date",
            "reason": "Reason",
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
        if args.get("checkinpunch_details"):
            args["checkinpunch_details"] = frappe.parse_json(args.get("checkinpunch_details"))
            
      
            
        # ? CREATE ATTENDANCE REGULARIZATION DOC
        attendance_regularization_doc = frappe.get_doc({
            "doctype": "Attendance Regularization",
            **args
        })
        attendance_regularization_doc.insert()
        frappe.db.commit()
        
    except Exception as e:
        # ? HANDLE ERRORS
        frappe.log_error("Error While Creating Attendance Regularization", str(e))
        frappe.clear_messages()
        frappe.local.response["message"] = {
            "success": False,
            "message": f"While Creating Attendance Regularization: {str(e)}",
            "data": None,
        }

    else:
        # ? HANDLE SUCCESS
        frappe.local.response["message"] = {
            "success": True,
            "message": "Attendance Regularization Created Successfully!",
            "data": attendance_regularization_doc,
        }
    

# ! prompt_hr.api.mobile.attendance_regularization.update
# ? UPDATE ATTENDANCE REGULARIZATION
@frappe.whitelist()
def update(**args):
    try:
        # ? MANDATORY FIELD FOR IDENTIFICATION
        if not args.get("name"):
            frappe.throw("Attendance Regularization 'name' is required to update the document", frappe.MandatoryError)

        # ? FETCH EXISTING DOC
        attendance_regularization_doc = frappe.get_doc("Attendance Regularization", args.get("name"))
        
        # ? PARSE CHILD TABLE JSON FIELDS
        if args.get("checkinpunch_details"):
            args["checkinpunch_details"] = frappe.parse_json(args.get("checkinpunch_details"))

        # ? UPDATE FIELDS
        for key, value in args.items():
            if key != "name":  # avoid overwriting the document name
                attendance_regularization_doc.set(key, value)

        attendance_regularization_doc.save()
        frappe.db.commit()
        

    except Exception as e:
        # ? HANDLE ERRORS
        frappe.log_error("Error While Updating Attendance Regularization", str(e))
        frappe.clear_messages()
        frappe.local.response["message"] = {
            "success": False,
            "message": f"While Updating Attendance Regularization: {str(e)}",
            "data": None,
        }

    else:
        # ? HANDLE SUCCESS
        frappe.local.response["message"] = {
            "success": True,
            "message": "Attendance Regularization Updated Successfully!",
            "data": attendance_regularization_doc,
        }

# ! prompt_hr.api.mobile.attendance_regularization.delete
# ? DELETE ATTENDANCE REGULARIZATION
@frappe.whitelist()
def delete(name=None):
    try:
        # ? CHECK MANDATORY FIELD
        if not name:
            frappe.throw("Attendance Regularization 'name' is required to delete the document", frappe.MandatoryError)
            
        # ? VERIFY DOCUMENT EXISTS
        if not frappe.db.exists("Attendance Regularization", name):
            frappe.throw(f"Request with name '{name}' does not exist", frappe.DoesNotExistError)       

        # ? DELETE THE DOCUMENT
        frappe.delete_doc("Attendance Regularization", name, ignore_permissions=True)
        frappe.db.commit()

    except Exception as e:
        # ? HANDLE ERRORS
        frappe.log_error("Error While Deleting Attendance Regularization", str(e))
        frappe.clear_messages()
        frappe.local.response["message"] = {
            "success": False,
            "message": f"While Deleting Attendance Regularization: {str(e)}",
            "data": None,
        }

    else:
        # ? HANDLE SUCCESS
        frappe.local.response["message"] = {
            "success": True,
            "message": "Attendance Regularization Deleted Successfully!",
            "data": {"name": name},
        }

from prompt_hr.py.workflow import get_workflow_transitions
# ! prompt_hr.api.mobile.attendance_regularization.workflow_actions
# ? GET UNIQUE WORKFLOW ACTIONS BASED ON STATE
@frappe.whitelist()
def get_action_fields(doc,logged_employee_id=None, requesting_employee_id=None):
    try:
                                
        transitions = get_workflow_transitions("Attendance Regularization", doc)

        # Format actions into dicts
        actions = []
        for transition in transitions:
            actions.append({"action": transition})        
    except Exception as e:
        # ? HANDLE ERRORS
        frappe.log_error("Error While Getting Workflow Actions", str(e))
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
            "message": "Workflow Actions Loaded Successfully!",
            "data": actions,
        }
        
    
from frappe.model.workflow import apply_workflow as attendance_regularization_workflow

@frappe.whitelist()
def apply_workflow(attendance_regularization, action):
    try:
        # ? FETCH THE DOCUMENT
        
        if not frappe.db.exists("Attendance Regularization", attendance_regularization):
            frappe.throw(
                f"Attendance Regularization: {attendance_regularization} Does Not Exist!",
                frappe.DoesNotExistError,
            )

        doc = frappe.get_doc("Attendance Regularization", attendance_regularization)

        # ? APPLY WORKFLOW ACTION
        updated_doc = attendance_regularization_workflow(doc, action)

        # ? SAVE CHANGES
        doc.save(ignore_permissions=True)
    except Exception as e:
        # ? HANDLE ERRORS
        frappe.log_error("Error While Applying Workflow Action", str(e))
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
            "message": f"Workflow Action '{action}' Applied Successfully!",
            "data": updated_doc.as_dict(),
        }