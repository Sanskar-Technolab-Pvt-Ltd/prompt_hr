import frappe


# ! prompt_hr.api.mobile.shift_request.list
# ? GET SHIFT REQUEST LIST
@frappe.whitelist()
def list(
    filters=None,
    or_filters=None,
    fields=["name","employee","from_date","to_date","shift_type","status"],
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

        # ? GET TOTAL COUNT (manually count the names matching filters)
        total_names = frappe.get_list(
            "Shift Request",
            filters=filters,
            or_filters=or_filters,
            fields=["name"],
            ignore_permissions=False
        )
        total_count = len(total_names)
        
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
            "count": total_count        
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
            
        # ? VERIFY DOCUMENT EXISTS
        if not frappe.db.exists("Shift Request", name):
            frappe.throw(f"Request with name '{name}' does not exist", frappe.DoesNotExistError)    

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




# ! prompt_hr.api.mobile.shift_type.list
# ? GET SHIFT TYPE LIST
@frappe.whitelist()
def shift_type_list(
    filters=None,
    or_filters=None,
    fields=["*"],
    order_by=None,
    limit_page_length=0,
    limit_start=0,
):
    try:

        # ? GET SHIFT TYPE LIST
        shift_type_list = frappe.get_list(
            "Shift Type",
            filters=filters,
            or_filters=or_filters,
            fields=frappe.parse_json(fields),
            order_by=order_by,
            limit_page_length=limit_page_length,
            limit_start=limit_start,
        )

        # ? GET TOTAL COUNT (manually count the names matching filters)
        total_names = frappe.get_list(
            "Shift Type",
            filters=filters,
            or_filters=or_filters,
            fields=["name"],
            ignore_permissions=False
        )
        total_count = len(total_names)
        
    except Exception as e:
        # ? HANDLE ERRORS
        frappe.log_error("Error While Getting Shift Type List", str(e))
        frappe.clear_messages()
        frappe.local.response["message"] = {
            "success": False,
            "message": f"While Getting Shift Type List: {str(e)}",
            "data": None,
        }

    else:
        # ? HANDLE SUCCESS
        frappe.local.response["message"] = {
            "success": True,
            "message": "Shift Type List Loaded Successfully!",
            "data": shift_type_list,
            "count": total_count        
        }
        
        


# ! prompt_hr.api.mobile.shift_request.apply_workflow
# ? APPLY WORKFLOW ACTION ON LEAVE APPLICATION
from frappe.model.workflow import apply_workflow

@frappe.whitelist()
def apply_shift_workflow(shift_request, action):
    try:
        # ? FETCH THE DOCUMENT
        
        if not frappe.db.exists("Shift Request", shift_request):
            frappe.throw(
                f"Shift Request: {shift_request} Does Not Exist!",
                frappe.DoesNotExistError,
            )

        doc = frappe.get_doc("Shift Request", shift_request)

        # ? APPLY WORKFLOW ACTION
        updated_doc = apply_workflow(doc, action)

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


# ! prompt_hr.api.mobile.shift_request.workflow_actions
# ? GET UNIQUE WORKFLOW ACTIONS BASED ON STATE

@frappe.whitelist()
def get_action_fields(workflow_state, employee, shift_request):
    try:
        # ? GET USER FROM EMPLOYEE
        user = frappe.db.get_value("Employee", employee, "user_id")
        if not user:
            frappe.throw(f"No User Linked With Employee {employee}")

        # ? FETCH USER ROLES
        roles = set(frappe.get_roles(user))

        # ? ALLOWED ROLES
        allowed_roles = {"S - Employee", "S - HR Director (Global Admin)"}

        # ? CHECK IF USER HAS ANY ONE ROLE
        if not roles.intersection(allowed_roles):
            frappe.throw("You do not have permission to perform workflow actions")

        # ? FETCH DOC
        shift_doc = frappe.get_doc("Shift Request", shift_request)

        # If self leave (same employee who applied)
        if shift_doc.employee == employee:
            # If user is NOT HR Director → return blank
            if "S - HR Director (Global Admin)" not in roles:
                frappe.local.response["message"] = {
                    "success": True,
                    "message": "No workflow actions available for self leave",
                    "data": [],
                }
                return
            
        # ? FETCH WORKFLOW FOR Shift Request
        workflow_name = frappe.db.get_value(
            "Workflow",
            {"document_type": "Shift Request"},
            "name"
        )

        if not workflow_name:
            frappe.throw(
                "No Workflow Found For Shift Request",
                frappe.DoesNotExistError,
            )

        workflow_doc = frappe.get_doc("Workflow", workflow_name)

        # ? COLLECT UNIQUE ACTIONS
                
        actions = []
        seen = set()
        for transition in workflow_doc.transitions:
            if transition.state == workflow_state:
                if transition.action not in seen:
                    seen.add(transition.action)
                    actions.append({"action": transition.action})


        if not actions:
            return

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
        