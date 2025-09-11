import frappe
from frappe.utils.file_manager import save_file
from prompt_hr.api.mobile.attendance_regularization import get_employees_with_session_user

# ! prompt_hr.api.mobile.leave_application.list
# ? GET LEAVE APPLICATION REQUEST LIST
@frappe.whitelist()
def list(
    filters=None,
    or_filters=None,
    fields=["name","employee","leave_type","from_date","to_date","status","total_leave_days","workflow_state"],
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
        parsed_fields = frappe.parse_json(fields)

        # Ensure required fields are included
        required_fields = ["employee"]
        for field in required_fields:
            if field not in parsed_fields:
                parsed_fields.append(field)

        
        # Fetch leave applications
        leave_application_list_raw = frappe.get_list(
            "Leave Application",
            filters=filters,
            or_filters=or_filters,
            fields=parsed_fields, 
            order_by=order_by,
            limit_page_length=limit_page_length,
            limit_start=limit_start,
            ignore_permissions=False
        )


        # # ? GET TOTAL COUNT
        # total_names = frappe.get_list(
        #     "Leave Application",
        #     filters=filters,
        #     or_filters=or_filters,
        #     fields=["name"],
        #     ignore_permissions=True
        # )
        total_count = len(leave_application_list_raw)
        

    except Exception as e:
        # ? HANDLE ERRORS
        frappe.log_error("Error While Getting Leave Application List", str(e))
        frappe.clear_messages()
        frappe.local.response["message"] = {
            "success": False,
            "message": f"While Getting Leave Application List: {str(e)}",
            "data": None,
        }

    else:
        # ? HANDLE SUCCESS
        frappe.local.response["message"] = {
            "success": True,
            "message": "Leave Application List Loaded Successfully!",
            "data": leave_application_list_raw,
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
        # ? EXTRA VALIDATION FOR HALF DAY
        if str(args.get("half_day")) in ("1", "true", "True"):
            if not args.get("half_day_date"):
                frappe.throw("Please Fill Half Day Date", frappe.MandatoryError)
            if not args.get("custom_half_day_time"):
                frappe.throw("Please Fill Half Day Time!", frappe.MandatoryError)
                
         # ? PARSE CHILD TABLE JSON FIELDS
        if args.get("custom_email_cc"):
            args["custom_email_cc"] = frappe.parse_json(args.get("custom_email_cc"))
            
        # ? CREATE LEAVE APPLICATION
        leave_application_request_doc = frappe.get_doc({
            "doctype": "Leave Application",
            **args
        })
        
        uploaded_files = frappe.request.files.getlist("file")

        if uploaded_files:
            # First file -> store in custom_attachment before insert
            first_file = uploaded_files[0]
            file_doc = save_file(
                first_file.filename,
                first_file.stream.read(),
                None,  # not attached to any doc yet
                None,
                is_private=0
            )
            leave_application_request_doc.custom_attachment = file_doc.file_url

        # Insert doc
        leave_application_request_doc.insert()
        frappe.db.commit()

        # Now attach the rest to the doc (after insert)
        for uploaded_file in uploaded_files[1:]:
            save_file(
                uploaded_file.filename,
                uploaded_file.stream.read(),
                "Leave Application",
                leave_application_request_doc.name,
                is_private=0
            )
        
    except Exception as e:
        # ? HANDLE ERRORS
        frappe.log_error("Error While Creating Leave Application", str(e))
        frappe.clear_messages()
        frappe.local.response["message"] = {
            "success": False,
            "message": f"While Creating Leave Application: {str(e)}",
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
            "message": f"While Updating Leave Application: {str(e)}",
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
            "message": f"While Deleting Leave Application: {str(e)}",
            "data": None,
        }

    else:
        # ? HANDLE SUCCESS
        frappe.local.response["message"] = {
            "success": True,
            "message": "Leave Application Deleted Successfully!",
            "data": {"name": name},
        }
        
from frappe.utils import today
from prompt_hr.py.leave_application import custom_get_leave_details        
# ! prompt_hr.api.mobile.leave_type.list
@frappe.whitelist()
def leave_type_list(
    filters=None,
    or_filters=None,
    fields=["*"],
    order_by=None,
    limit_page_length=0,
    limit_start=0,
):
    try:

        leave_type_list = frappe.get_list(
            "Leave Type",
            filters=filters,
            or_filters=or_filters,
            fields=frappe.parse_json(fields),
            order_by=order_by,
            limit_page_length=limit_page_length,
            limit_start=limit_start,
        )
        
        user = frappe.session.user
        employee = frappe.get_value("Employee", {"user_id": user}, "name")
        date = today()
        # get raw data from your custom function
        result = custom_get_leave_details(employee, date)

        leave_allocation = result.get("leave_allocation", {})
        lwps = result.get("lwps", [])
        employee_name = frappe.db.get_value("Employee", employee, "employee_name")

        # transform data
        leave_data = []

        # 1. loop over leave allocations
        for leave_type, details in leave_allocation.items():
            leave_data.append({
                "name": leave_type,
                # "employee": employee,
                # "employee_name": employee_name,
                # "opening_balance": details.get("total_leaves", 0.0),
                # "leaves_taken": details.get("leaves_taken", 0.0),
                # "closing_balance": details.get("remaining_leaves", 0.0)
            })
        
        leave_application_list = frappe.get_list(
            "Leave Type",fields=["name"],filters={"is_lwp": 1})
        
        for leave_app in leave_application_list:
            leave_data.append({
                "name": leave_app.name,
            })
        
        final_leave_type = []
        for leave in leave_type_list:
            if leave.name in [ld['name'] for ld in leave_data]:
                final_leave_type.append(leave)
                
                
        print(final_leave_type)
        # print(leave_type_list)
        total_count = len(final_leave_type)
        
    except Exception as e:
        # ? HANDLE ERRORS
        frappe.log_error("Error While Getting Leave Type List", str(e))
        frappe.clear_messages()
        frappe.local.response["message"] = {
            "success": False,
            "message": f"While Getting Leave Type List: {str(e)}",
            "data": None,
        }

    else:
        # ? HANDLE SUCCESS
        frappe.local.response["message"] = {
            "success": True,
            "message": "Leave Type List Loaded Successfully!",
            "data": final_leave_type,
            "count": total_count        
        }
        
        
 


# ! prompt_hr.api.mobile.leave_application.apply_workflow
# ? APPLY WORKFLOW ACTION ON LEAVE APPLICATION
from frappe.model.workflow import apply_workflow

@frappe.whitelist()
def apply_leave_workflow(leave_application, action):
    try:
        # ? FETCH THE DOCUMENT
        
        if not frappe.db.exists("Leave Application", leave_application):
            frappe.throw(
                f"Leave Application: {leave_application} Does Not Exist!",
                frappe.DoesNotExistError,
            )

        doc = frappe.get_doc("Leave Application", leave_application)

        # ? APPLY WORKFLOW ACTION
        if action == "Reject":
            doc.status = "Rejected"
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


from prompt_hr.py.workflow import get_workflow_transitions

# ! prompt_hr.api.mobile.leave_application.workflow_actions
# ? GET UNIQUE WORKFLOW ACTIONS BASED ON STATE

@frappe.whitelist()
def get_action_fields(workflow_state, employee, leave_application):
    try:
        
        transitions = get_workflow_transitions("Leave Application", leave_application)

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
