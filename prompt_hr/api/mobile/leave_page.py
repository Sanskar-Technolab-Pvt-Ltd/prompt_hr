
import frappe
from frappe.desk.query_report import run

# ! prompt_hr.api.mobile.reports.employee_leave_balance.run
# ? RUN EMPLOYEE LEAVE BALANCE REPORT
@frappe.whitelist()
def get(**args):
    try:
        # ? DEFINE MANDATORY FIELDS
        mandatory_fields = {
            "from_date": "From Date",
            "to_date": "To Date",
            # "company": "Company",
            # "employee": "Employee"
        }

        # ? CHECK MANDATORY FIELDS
        for field, field_name in mandatory_fields.items():
            if not args.get(field):
                frappe.throw(f"Please Fill {field_name} Field!", frappe.MandatoryError)

        # ? DEFAULT VALUES
        filters = {
            "from_date": args.get("from_date"),
            "to_date": args.get("to_date"),
            "company": args.get("company"),
            "employee": args.get("employee"),
            "employee_status": args.get("employee_status") or "Active",
            "consolidate_leave_types": int(args.get("consolidate_leave_types") or 1),
        }

        # ? RUN REPORT
        report_data = run("Employee Leave Balance", filters=filters)
        result_data = report_data.get("result", [])
        
         # Process the data to include both leave types and employee details
        formatted_data = []
        current_leave_type = None
        
        for row in result_data:
            if "leave_type" in row and "employee" not in row:
                # This is a leave type header row
                current_leave_type = row["leave_type"]
            elif "employee" in row:
                # This is an employee detail row
                formatted_data.append({
                    "leave_type": current_leave_type,
                    "employee": row.get("employee"),
                    "employee_name": row.get("employee_name"),
                    "opening_balance": row.get("opening_balance"),
                    "leaves_taken": row.get("leaves_taken"),
                    "closing_balance": row.get("closing_balance")
                })

    except Exception as e:
        frappe.log_error("Error Running Employee Leave Balance Report", str(e))
        frappe.clear_messages()
        frappe.local.response["message"] = {
            "success": False,
            "message": f"Error Running Report: {str(e)}",
            "data": None,
        }

    else:
        frappe.local.response["message"] = {
            "success": True,
            "message": "Employee Leave Balance Report Fetched Successfully!",
            "data": formatted_data,
        }
