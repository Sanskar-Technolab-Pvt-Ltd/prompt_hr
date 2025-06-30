import frappe
from frappe.desk.query_report import run

@frappe.whitelist()
def get(**args):
    try:
        # Define mandatory fields
        mandatory_fields = {
            "from_date": "From Date",
            "to_date": "To Date",
        }

        # Check mandatory fields
        for field, field_name in mandatory_fields.items():
            if not args.get(field):
                frappe.throw(f"Please Fill {field_name} Field!", frappe.MandatoryError)

        # Set up filters
        filters = {
            "from_date": args.get("from_date"),
            "to_date": args.get("to_date"),
            "company": args.get("company"),
            "employee": args.get("employee"),
            "employee_status": args.get("employee_status") or "Active",
            "consolidate_leave_types": int(args.get("consolidate_leave_types") or 1),
        }

        # Run report
        report_data = run("Employee Leave Balance", filters=filters)
        result_data = report_data.get("result", [])
        
        # Process the data differently based on whether employee filter is applied
        formatted_data = []
        
        if args.get("employee"):
            # When employee filter is applied, the structure is different
            for row in result_data:
                if isinstance(row, dict) and "employee" in row:
                    formatted_data.append({
                        "leave_type": row.get("leave_type"),
                        "employee": row.get("employee"),
                        "employee_name": row.get("employee_name"),
                        "opening_balance": row.get("opening_balance"),
                        "leaves_taken": row.get("leaves_taken"),
                        "closing_balance": row.get("closing_balance")
                    })
        else:
            # Original processing for non-filtered case
            current_leave_type = None
            for row in result_data:
                if isinstance(row, dict):
                    if "leave_type" in row and "employee" not in row:
                        current_leave_type = row["leave_type"]
                    elif "employee" in row:
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