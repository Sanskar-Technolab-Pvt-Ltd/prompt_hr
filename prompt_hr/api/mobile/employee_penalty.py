import frappe
from prompt_hr.api.mobile.attendance_regularization import get_employees_with_session_user

# ! prompt_hr.api.mobile.employee_penalty.list
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
        
        employee_penalty_list = frappe.get_list(
            "Employee Penalty",
            filters=filters,
            or_filters=or_filters,
            fields=frappe.parse_json(fields),
            order_by=order_by,
            limit_page_length=limit_page_length,
            limit_start=limit_start,
        )
                
        total_count = len(employee_penalty_list)

    except Exception as e:
        # ? HANDLE ERRORS
        frappe.log_error("Error While Getting Attendance Regularization List", str(e))
        frappe.clear_messages()
        frappe.local.response["message"] = {
            "success": False,
            "message": f"While Getting Employee Penalty List: {str(e)}",
            "data": None,
        }

    else:
        # ? HANDLE SUCCESS
        frappe.local.response["message"] = {
            "success": True,
            "message": "Employee Penalty List Loaded Successfully!",
            "data": employee_penalty_list,
            "count": total_count        
        }
# ! prompt_hr.api.mobile.employee_penalty_list.get
@frappe.whitelist()
def get(name):
    try: 
        employee_penalty_list_exists = frappe.db.exists("Employee Penalty", name)
        
        if not employee_penalty_list_exists:
            frappe.throw(
                f"Employee Penalty: {name} Does Not Exists!",
                frappe.DoesNotExistError,
            )

        doc = frappe.get_doc("Employee Penalty", name)

        # Build a filtered dict for response
        data = {
            "name": doc.name,
            "employee": doc.employee,
            "company": doc.company,
            "penalty_date": doc.penalty_date,
            "total_leave_penalty": doc.total_leave_penalty,
            "leave_penalty_details": [
                {
                    "idx": d.idx,
                    "leave_type": d.leave_type,
                    "leave_amount": d.leave_amount,
                    "reason": d.reason,
                    "remarks": d.remarks,
                }
                for d in doc.leave_penalty_details
            ],
        }

    except Exception as e:
        frappe.log_error("While Getting Employee Penalty Detail", str(e))
        frappe.clear_messages()
        frappe.local.response["message"] = {
            "success": False,
            "message": str(e),
            "data": None,
        }

    else:
        frappe.local.response["message"] = {
            "success": True,
            "message": "Employee Penalty Loaded Successfully!",
            "data": data,
        }
