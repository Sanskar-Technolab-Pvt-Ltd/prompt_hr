import frappe
from prompt_hr.py.utils import is_user_reporting_manager_or_hr
from prompt_hr.api.mobile.attendance_regularization import get_employees_with_session_user
# ! prompt_hr.api.mobile.attendance_request.list
# ? GET ATTENDANCE REQUEST LIST
@frappe.whitelist()
def list(
    filters=None,
    or_filters=None,
    fields=["name","employee","from_date","to_date","reason","custom_status","workflow_state"],
    order_by=None,
    limit_page_length=0,
    limit_start=0,
):
    try:
        # --- Get employees allowed for session user ---
        employees_data = get_employees_with_session_user()
        if not employees_data.get("success"):
            frappe.throw(employees_data.get("message", "Unable to fetch employees"))

        employee_list = [emp["name"] for emp in employees_data["employees"]]

        # --- Parse filters from request ---
        if filters:
            filters = frappe.parse_json(filters)
        else:
            filters = []

        # Convert filters to list-of-lists always
        if isinstance(filters, dict):
            filters = [[k, "=", v] for k, v in filters.items()]

        # Always enforce employee filter (session + request)
        filters.append(["employee", "in", employee_list])

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

        for row in attendance_request_list:
            row["custom_status"] = row.get("workflow_state")
            
        # ? GET TOTAL COUNT (manually count the names matching filters)
        total_names = frappe.get_list(
            "Attendance Request",
            filters=filters,
            or_filters=or_filters,
            fields=["name"],
            ignore_permissions=False
        )
        total_count = len(total_names)

    except Exception as e:
        # ? HANDLE ERRORS
        frappe.log_error("Error While Getting Attendance Request List", str(e))
        frappe.clear_messages()
        frappe.local.response["message"] = {
            "success": False,
            "message": f"While Getting Attendance Request List: {str(e)}",
            "data": None,
        }

    else:
        # ? HANDLE SUCCESS
        frappe.local.response["message"] = {
            "success": True,
            "message": "Attendance Request List Loaded Successfully!",
            "data": attendance_request_list,
            "count": total_count
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
        1
        # Convert to dict (so we can override values)
        attendance_request_dict = attendance_request.as_dict()

        # Override custom_status with workflow_state
        attendance_request_dict["custom_status"] = attendance_request_dict.get("workflow_state")


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
            "data": attendance_request_dict,
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

        # ? CAST custom_partial_day_request_minutes TO INT IF PRESENT
        if args.get("custom_partial_day_request_minutes"):
            try:
                args["custom_partial_day_request_minutes"] = int(
                    args.get("custom_partial_day_request_minutes")
                )
            except ValueError:
                frappe.throw("Partial Day Minutes must be a number")

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
            "message": f"While Creating Attendance Request: {str(e)}",
            "data": None,
        }

    else:
        # ? HANDLE SUCCESS
        frappe.local.response["message"] = {
            "success": True,
            "message": "Attendance Request Created Successfully!",
            "data": attendance_request_doc.as_dict(),
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
            "message": f"While Updating Attendance Request: {str(e)}",
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
            "message": f"While Deleting Attendance Request: {str(e)}",
            "data": None,
        }

    else:
        # ? HANDLE SUCCESS
        frappe.local.response["message"] = {
            "success": True,
            "message": "Attendance Request Deleted Successfully!",
            "data": {"name": name},
        }

from prompt_hr.py.workflow import get_workflow_transitions
# ! prompt_hr.api.mobile.attendance_request.workflow_actions
# ? GET UNIQUE WORKFLOW ACTIONS BASED ON STATE
@frappe.whitelist()
def get_action_fields(doc, logged_employee_id=None, requesting_employee_id=None):
    try:
        transitions = get_workflow_transitions("Attendance Request", doc)

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
        
    
from frappe.model.workflow import apply_workflow as attendance_request_workflow
@frappe.whitelist()
def apply_workflow(attendance_request, action, custom_reason_for_rejection=None):
    try:
        # ? FETCH THE DOCUMENT
        
        if not frappe.db.exists("Attendance Request", attendance_request):
            frappe.throw(
                f"Attendance Request: {attendance_request} Does Not Exist!",
                frappe.DoesNotExistError,
            )

        doc = frappe.get_doc("Attendance Request", attendance_request)
        
     
        if action == "Reject":
            if not custom_reason_for_rejection:
                custom_reason_for_rejection = "No Reason Provided"
            
        # ? APPLY WORKFLOW ACTION
        updated_doc = attendance_request_workflow(doc, action)
        updated_doc.db_set("custom_reason_for_rejection",custom_reason_for_rejection)

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