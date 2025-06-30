import frappe

# ! prompt_hr.api.mobile.attendance.list
# ? GET ATTENDANCE LIST
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

        # ? GET ATTENDANCE LIST
        attendance_list = frappe.get_list(
            "Attendance",
            filters=filters,
            or_filters=or_filters,
            fields=frappe.parse_json(fields),
            order_by=order_by,
            limit_page_length=limit_page_length,
            limit_start=limit_start,
        )
        
        # ? GET TOTAL COUNT (manually count the names matching filters)
        total_names = frappe.get_list(
            "Attendance",
            filters=filters,
            or_filters=or_filters,
            fields=["name"],
            ignore_permissions=False
        )
        
        total_count = len(total_names)
        
    except Exception as e:
        # ? HANDLE ERRORS
        frappe.log_error("Error While Getting Attendance List", str(e))
        frappe.clear_messages()
        frappe.local.response["message"] = {
            "success": False,
            "message": f"Error While Getting Attendance List: {str(e)}",
            "data": None,
        }

    else:
        # ? HANDLE SUCCESS
        frappe.local.response["message"] = {
            "success": True,
            "message": "Attendance List Loaded Successfully!",
            "data": attendance_list,
            "count": total_count        
        }
          
# ! prompt_hr.api.mobile.attendance.get
# ? GET ATTENDANCE DETAIL
@frappe.whitelist()
def get(name):
    try:
        # ? CHECK IF ATTENDANCE  DOC EXISTS OR NOT
        attendance_exists = frappe.db.exists("Attendance", name)

        # ? IF ATTENDANCE  DOC NOT
        if not attendance_exists:
            frappe.throw(
                f"Attendance: {name} Does Not Exists!",
                frappe.DoesNotExistError,
            )

        # ? GET ATTENDANCE  DOC
        attendance = frappe.get_doc("Attendance", name)

    except Exception as e:
        # ? HANDLE ERRORS
        frappe.log_error("Error While Getting Attendance Detail", str(e))
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
            "message": "Attendance Loaded Successfully!",
            "data": attendance,
        }
    
import frappe
from datetime import datetime
from frappe.utils import get_first_day, get_last_day

@frappe.whitelist()
def attendance_calendar_list(
    employee=None,
    order_by=None,
    limit_page_length=0,
    limit_start=0,
):
    try:
        if not employee:
            frappe.throw("Employee is required")

        # Get current month's start and end date
        today = datetime.today()
        month_start = get_first_day(today).strftime("%Y-%m-%d")
        month_end = get_last_day(today).strftime("%Y-%m-%d")

        # Filters: by employee name and current month
        filters = {
            "employee": employee,
            "attendance_date": ["between", [month_start, month_end]],
            "docstatus":1
        }

        # Fields to return
        selected_fields = [
            "attendance_date",
            "employee_name",
            "name",
            "employee",
            "status"
        ]

        # Fetch attendance list
        attendance_list = frappe.get_list(
            "Attendance",
            filters=filters,
            fields=selected_fields,
            order_by=order_by,
            limit_page_length=limit_page_length,
            limit_start=limit_start,
        )

        # ? GET TOTAL COUNT (manually count the names matching filters)
        total_names = frappe.get_list(
            "Attendance",
            filters=filters,
            fields=["name"],
            ignore_permissions=False
        )
        
        total_count = len(total_names)

    except Exception as e:
        frappe.log_error("Error While Getting Attendance List", str(e))
        frappe.clear_messages()
        frappe.local.response["message"] = {
            "success": False,
            "message": f"Error While Getting Attendance List: {str(e)}",
            "data": None,
        }

    else:
        frappe.local.response["message"] = {
            "success": True,
            "message": "Attendance List Loaded Successfully!",
            "data": attendance_list,
            "count": total_count        
        }
