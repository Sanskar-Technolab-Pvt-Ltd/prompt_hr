import time
import frappe
from frappe.desk.query_report import get_prepared_report_result

# @frappe.whitelist()
# def get(**args):
#     try:
#         # Validate required fields
#         for field, label in {"from_date": "From Date", "to_date": "To Date"}.items():
#             if not args.get(field):
#                 frappe.throw(f"Please fill {label} field!", frappe.MandatoryError)

#         filters = {
#             "from_date": args.get("from_date"),
#             "to_date": args.get("to_date"),
#             "company": args.get("company"),
#             "employee": args.get("employee"),
#             "employee_status": args.get("employee_status") or "Active",
#             "consolidate_leave_types": int(args.get("consolidate_leave_types") or 1),
#         }

#         report_name = "Employee Leave Balance"
#         report_filters_json = frappe.as_json(filters)

#         # Always create a new Prepared Report
#         prepared_doc = frappe.get_doc({
#             "doctype": "Prepared Report",
#             "report_name": report_name,
#             "filters": report_filters_json,
#             "status": "Queued",
#             "report_type": "Script Report",
#             "user": frappe.session.user
#         })
#         prepared_doc.insert(ignore_permissions=True)

#         frappe.enqueue(
#             method="frappe.desk.query_report.run_report_job",
#             queue="long",
#             timeout=300,
#             report_name=report_name,
#             filters=filters,
#             user=frappe.session.user
#         )

#         # Wait for Prepared Report to be completed
#         max_wait = 30
#         waited = 0
#         interval = 2
#         report_name_id = None

#         while waited < max_wait:
#             frappe.db.commit()
#             completed = frappe.get_all(
#                 "Prepared Report",
#                 filters={
#                     "name": prepared_doc.name,
#                     "status": "Completed"
#                 },
#                 fields=["name"]
#             )
#             if completed:
#                 report_name_id = completed[0]["name"]
#                 break

#             time.sleep(interval)
#             waited += interval

#         if not report_name_id:
#             frappe.throw("Report generation timed out. Please try again later.")

#         # Fetch prepared report result
#         report_doc = frappe.get_doc("Report", report_name)
#         raw_result = get_prepared_report_result(report_doc, filters, report_name_id, frappe.session.user)
#         result_data = raw_result.get("result", []) if isinstance(raw_result, dict) else []
#         formatted_data = []

#         if args.get("employee"):
#             for row in result_data:
#                 if isinstance(row, dict) and "employee" in row:
#                     formatted_data.append({
#                         "leave_type": row.get("leave_type"),
#                         "employee": row.get("employee"),
#                         "employee_name": row.get("employee_name"),
#                         "opening_balance": row.get("opening_balance"),
#                         "leaves_taken": row.get("leaves_taken"),
#                         "closing_balance": row.get("closing_balance")
#                     })
#         else:
#             current_leave_type = None
#             for row in result_data:
#                 if isinstance(row, dict):
#                     if "leave_type" in row and "employee" not in row:
#                         current_leave_type = row["leave_type"]
#                     elif "employee" in row:
#                         formatted_data.append({
#                             "leave_type": current_leave_type,
#                             "employee": row.get("employee"),
#                             "employee_name": row.get("employee_name"),
#                             "opening_balance": row.get("opening_balance"),
#                             "leaves_taken": row.get("leaves_taken"),
#                             "closing_balance": row.get("closing_balance")
#                         })

#     except Exception as e:
#         frappe.log_error("Error Running Employee Leave Balance Report", frappe.get_traceback())
#         frappe.clear_messages()
#         frappe.local.response["message"] = {
#             "success": False,
#             "message": f"Running Report: {str(e)}",
#             "data": None
#         }
#     else:
#         frappe.local.response["message"] = {
#             "success": True,
#             "message": "Employee Leave Balance Report Fetched Successfully!",
#             "data": formatted_data
#         }


from frappe.utils import today
from prompt_hr.py.leave_application import custom_get_leave_details

@frappe.whitelist()
def get(employee):
    try:
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
                "leave_type": leave_type,
                "employee": employee,
                "employee_name": employee_name,
                "opening_balance": details.get("total_leaves", 0.0),
                "leaves_taken": details.get("leaves_taken", 0.0),
                "closing_balance": details.get("remaining_leaves", 0.0)
            })

        frappe.local.response["message"] = {
            "success": True,
            "message": "Employee Leave Balance Report Fetched Successfully!",
            "data": leave_data,
        }

    except Exception as e:
        frappe.log_error("Error Running Employee Leave Balance Report", str(e))
        # frappe.clear_messages()
        frappe.local.response["message"] = {
            "success": False,
            "message": f"Running Report: {str(e)}",
            "data": None,
        }
