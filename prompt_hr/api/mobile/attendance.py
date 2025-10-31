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
            "message": f"While Getting Attendance List: {str(e)}",
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

import json 
from datetime import datetime
from frappe.utils import get_first_day, get_last_day

@frappe.whitelist()
def attendance_calendar_list(
    employee=None,
    order_by=None,
    attendance_date=None,
    limit_page_length=0,
    limit_start=0,
):
    try:
        if not employee:
            frappe.throw("Employee is required")

        if attendance_date and isinstance(attendance_date, str):
            attendance_date = json.loads(attendance_date)
        # Get current month's start and end date
        today = datetime.today()
        month_start = get_first_day(today).strftime("%Y-%m-%d")
        month_end = get_last_day(today).strftime("%Y-%m-%d")

        # Filters: by employee name and current month
        filters = {
            "employee": employee,
            "attendance_date": ["between", [month_start, month_end]] if not attendance_date else attendance_date,
            "docstatus": 1,
        }

        # Fields to return
        selected_fields = [
            "attendance_date",
            "employee_name",
            "name",
            "employee",
            "status",
            "leave_application",
            "custom_employee_penalty_id"
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

        for attendance in attendance_list:

            attendance["leave_total"] = 0

            if attendance.get("status") == "On Leave":
                
                attendance["leave_total"] = 1
                
            elif attendance.get("status") == "Half Day" and attendance.get("Leave Application"):
                attendance["leave_total"] = 0.5

            if attendance.get("custom_employee_penalty_id"):
                attendance["total_penalty"] = frappe.db.get_value("Employee Penalty", attendance.get("custom_employee_penalty_id"), "total_leave_penalty")


        # Get HR Settings and build a status → label map
        hr_settings = frappe.get_single("HR Settings")
        status_map = {}
        if hr_settings and hr_settings.custom_attendance_staus:
            for row in hr_settings.custom_attendance_staus:
                label_value = row.label if hasattr(row, "label") and row.label else row.status
                status_map[row.status] = label_value

        # Replace status with label (if exists)
        for att in attendance_list:
            att["status"] = status_map.get(att["status"], att["status"])
        
        holiday_list_name = frappe.db.get_value("Employee", employee, "holiday_list")
        holiday_entries = []
        if holiday_list_name:
            holidays = frappe.get_all(
                "Holiday",
                filters={
                    "parent": holiday_list_name,
                    "holiday_date": ["between", [month_start, month_end]],
                },
                fields=["holiday_date"],
            )

            # Convert holidays to same structure as attendance_list
            for h in holidays:
                holiday_entries.append({
                    "attendance_date": h.holiday_date,
                    "employee_name": frappe.db.get_value("Employee", employee, "employee_name"),
                    "employee": employee,
                    "status": "No Attendance",
                })

        all_entries = attendance_list + holiday_entries

        all_entries.sort(key=lambda x: x.get("attendance_date"))

        total_count = len(all_entries)

    except Exception as e:
        frappe.log_error("Error While Getting Attendance List", str(e))
        frappe.clear_messages()
        frappe.local.response["message"] = {
            "success": False,
            "message": f"While Getting Attendance List: {str(e)}",
            "data": None,
        }

    else:
        frappe.local.response["message"] = {
            "success": True,
            "message": "Attendance List Loaded Successfully!",
            "data": all_entries,
            "count": total_count,
        }



@frappe.whitelist()
def attendance_status():
    try:
        attendance_status_list = []
        hr_settings = frappe.get_single("HR Settings")

        if hr_settings:
            seen = set()  # to track unique (color, label) pairs
            for status in hr_settings.custom_attendance_staus:
                color_value = status.color if getattr(status, "color", None) else status.status
                label_value = status.label if getattr(status, "label", None) else status.status
                is_default = status.is_default if getattr(status, "is_default", None) else 0

                key = (color_value, label_value)
                if key not in seen:
                    seen.add(key)
                    attendance_status_list.append({
                        "color": color_value,
                        "label": label_value,
                        "is_default":is_default
                    })

    except Exception as e:
        frappe.log_error("Error While Getting Attendance Status Detail", str(e))
        frappe.clear_messages()
        frappe.local.response["message"] = {
            "success": False,
            "message": str(e),
            "data": None,
        }

    else:
        frappe.local.response["message"] = {
            "success": True,
            "message": "Attendance Status Loaded Successfully!",
            "data": attendance_status_list,
            "count": len(attendance_status_list)
        }
