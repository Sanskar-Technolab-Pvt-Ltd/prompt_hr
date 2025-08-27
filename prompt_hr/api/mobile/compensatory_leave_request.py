import frappe
from frappe.utils.file_manager import save_file
from prompt_hr.py.utils import is_user_reporting_manager_or_hr

# compensatory_leave_request
# Compensatory Leave Request
# COMPENSATORY LEAVE REQUEST

# ! prompt_hr.api.mobile.compensatory_leave_request.list
# ? GET Compensatory Leave Request LIST
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
        # ? GET Compensatory Leave Request List
        compensatory_leave_request_list = frappe.get_list(
            "Compensatory Leave Request",
            filters=filters,
            or_filters=or_filters,
            fields=frappe.parse_json(fields),
            order_by=order_by,
            limit_page_length=limit_page_length,
            limit_start=limit_start,
            ignore_permissions=False
        )
        
       
        total_count = len(compensatory_leave_request_list)

    except Exception as e:
        # ? HANDLE ERRORS
        frappe.log_error("Error While Getting Compensatory Leave Request List", str(e))
        frappe.clear_messages()
        frappe.local.response["message"] = {
            "success": False,
            "message": f"While Getting Compensatory Leave Request List: {str(e)}",
            "data": None,
        }

    else:
        # ? HANDLE SUCCESS
        frappe.local.response["message"] = {
            "success": True,
            "message": "Compensatory Leave Request List Loaded Successfully!",
            "data": compensatory_leave_request_list,
            "count": total_count        
        }

# ! prompt_hr.api.mobile.compensatory_leave_request.get
# ? GET COMPENSATORY LEAVE REQUEST DETAIL
@frappe.whitelist()
def get(name):
    try: 
        # ? CHECK IF COMPENSATORY LEAVE REQUEST DOC EXISTS OR NOT
        compensatory_leave_request_exists = frappe.db.exists("Compensatory Leave Request", name)

        # ? IF COMPENSATORY LEAVE REQUEST DOC NOT
        if not compensatory_leave_request_exists:
            frappe.throw(
                f"Compensatory Leave Request: {name} Does Not Exists!",
                frappe.DoesNotExistError,
            )

        # ? GET COMPENSATORY LEAVE REQUEST DOC
        compensatory_leave_request = frappe.get_doc("Compensatory Leave Request", name)

    except Exception as e:
        # ? HANDLE ERRORS
        frappe.log_error("While Getting Compensatory Leave Request Detail", str(e))
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
            "message": "Compensatory Leave Request Loaded Successfully!",
            "data": compensatory_leave_request,
        }
        
        

# ! prompt_hr.api.mobile.compensatory_leave_request.create  
# ? CREATE COMPENSATORY LEAVE REQUEST
@frappe.whitelist()
def create(**args):
    try:
        # ? DEFINE MANDATORY FIELDS
        mandatory_fields = {
            "employee": "Employee",
            "work_from_date": "Week From Date",
            "work_end_date": "Work End Date",
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
      
            
        # ? CREATE COMPENSATORY LEAVE REQUEST DOC
        compensatory_leave_request_doc = frappe.get_doc({
            "doctype": "Compensatory Leave Request",
            **args
        })
        compensatory_leave_request_doc.insert()
        frappe.db.commit()
        
    except Exception as e:
        # ? HANDLE ERRORS
        frappe.log_error("Error While Creating Compensatory Leave Request", str(e))
        frappe.clear_messages()
        frappe.local.response["message"] = {
            "success": False,
            "message": f"While Creating Compensatory Leave Request: {str(e)}",
            "data": None,
        }

    else:
        # ? HANDLE SUCCESS
        frappe.local.response["message"] = {
            "success": True,
            "message": "Compensatory Leave Request Created Successfully!",
            "data": compensatory_leave_request_doc,
        }
    

from frappe.model.workflow import apply_workflow as attendance_request_workflow
from prompt_hr.py.workflow import get_workflow_transitions
 
# ! prompt_hr.api.mobile.compensatory_leave_request.workflow_actions
# ? GET UNIQUE WORKFLOW ACTIONS BASED ON STATE
@frappe.whitelist()
def get_action_fields(compensatory_leave_request,workflow_state=None, employee=None):
    try:
        
        transitions = get_workflow_transitions("Compensatory Leave Request", compensatory_leave_request)

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
        
 
# ! prompt_hr.api.mobile.compensatory_leave_request.apply_workflow
# ? APPLY WORKFLOW ACTION ON LEAVE APPLICATION
@frappe.whitelist()
def apply_workflow(compensatory_leave_request, action):
    try:
        # ? FETCH THE DOCUMENT
        
        if not frappe.db.exists("Compensatory Leave Request", compensatory_leave_request):
            frappe.throw(
                f"Compensatory Leave Request: {compensatory_leave_request} Does Not Exist!",
                frappe.DoesNotExistError,
            )
 
        doc = frappe.get_doc("Compensatory Leave Request", compensatory_leave_request)
 
        # ? APPLY WORKFLOW ACTION
        updated_doc = attendance_request_workflow(doc, action)
 
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
        
        
 
# ! prompt_hr.api.mobile.compensatory_leave_request.get_leave_type
# ? FETCH LEAVE TYPES
@frappe.whitelist()
def get_leave_type():
    try:
        
        leave_types = []
        leave_types = frappe.db.get_list("Leave Type", {"is_compensatory": 1}, "leave_type_name") or []
        
    except Exception as e:
        # ? HANDLE ERRORS
        frappe.log_error("Error While Fetching Leave Types", str(e))
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
            "message": "Leave Types Loaded Successfully!",
            "data": leave_types,
        }
        
 