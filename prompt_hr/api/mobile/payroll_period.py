import frappe
from frappe.utils import getdate, nowdate

# ! prompt_hr.api.mobile.payroll_period.list
# ? GET PAYROLL PERIOD LIST
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

        # ? GET PAYROLL PERIOD LIST
        today = getdate(nowdate())
        payroll_period_list = frappe.get_list(
            "Payroll Period",
            filters=filters,
            or_filters=or_filters,
            fields=frappe.parse_json(fields),
            order_by=order_by,
            limit_page_length=limit_page_length,
            limit_start=limit_start,
        )
        
        # Add current_period key
        for period in payroll_period_list:
            if period.get("start_date") and period.get("end_date"):
                period["current_period"] = "Yes" if period["start_date"] <= today <= period["end_date"] else "No"
            else:
                period["current_period"] = "No"
        
        # ? GET TOTAL COUNT (manually count the names matching filters)
        total_names = frappe.get_list(
            "Payroll Period",
            filters=filters,
            or_filters=or_filters,
            fields=["name"],
            ignore_permissions=False
        )
        total_count = len(total_names)

    except Exception as e:
        # ? HANDLE ERRORS
        frappe.log_error("Error While Getting Payroll Period List", str(e))
        frappe.clear_messages()
        frappe.local.response["message"] = {
            "success": False,
            "message": f"Error While Getting Payroll Period List: {str(e)}",
            "data": None,
        }
        
        

    else:
        # ? HANDLE SUCCESS
        frappe.local.response["message"] = {
            "success": True,
            "message": "Payroll Period List Loaded Successfully!",
            "data": payroll_period_list,
            "count": total_count        
        }
          
# ! prompt_hr.api.mobile.payroll_period.get
# ? GET PAYROLL PERIOD DETAIL
@frappe.whitelist()
def get(name):
    try:
        
        # ? CHECK IF PAYROLL PERIOD  DOC EXISTS OR NOT
        payroll_period_exists = frappe.db.exists("Payroll Period", name)

        # ? IF PAYROLL PERIOD  DOC NOT
        if not payroll_period_exists:
            frappe.throw(
                f"Payroll Period: {name} Does Not Exists!",
                frappe.DoesNotExistError,
            )

        # Get the Payroll Period doc
        payroll_period = frappe.get_doc("Payroll Period", name)
        data = payroll_period.as_dict()

        # Get today's date as date object
        today = getdate(nowdate())

        # Check if current period
        if data.get("start_date") and data.get("end_date"):
            start = getdate(data["start_date"])
            end = getdate(data["end_date"])
            data["current_period"] = "Yes" if start <= today <= end else "No"
        else:
            data["current_period"] = "No"
        
        

    except Exception as e:
        # ? HANDLE ERRORS
        frappe.log_error("Error While Getting Payroll Period Detail", str(e))
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
            "message": "Payroll Period Loaded Successfully!",
            "data": data,
        }