# ! prompt_hr.api.mobile.upcoming_shift.list
# ? GET FUTURE SHIFT ASSIGNMENTS (WHERE end_date IS NOT NULL)
import frappe
import json

@frappe.whitelist()
def list(
    filters=None,
    or_filters=None,
    fields=["name","employee","shift_type","start_date","end_date"],
    order_by="start_date asc",
    limit_page_length=0,
    limit_start=0,
):
    try:
        from frappe.utils import nowdate

        #   # Initialize default values
        # if fields is None:
        #     fields = ["shift_type", "start_date", "end_date"]
        
        # Parse incoming parameters
        if isinstance(filters, str):
            filters = json.loads(filters)
        if isinstance(or_filters, str):
            or_filters = json.loads(or_filters)
        if isinstance(fields, str):
            fields = json.loads(fields)
        
        # Ensure filters is a dict
        if not isinstance(filters, dict):
            filters = {}
        
        # Add mandatory conditions
        filters.update({
            "start_date": [">", nowdate()],
            "end_date": ["is", "set"],
            "docstatus": 1  # Exclude submitted
        })

          # Get Shift Assignment List
        shift_assignment_list = frappe.get_list(
            "Shift Assignment",
            filters=filters,
            or_filters=or_filters,
            fields=fields,
            order_by=order_by,
            limit_page_length=limit_page_length,
            limit_start=limit_start,
        )

        # ? GET TOTAL COUNT
        total_names = frappe.get_all(
            "Shift Assignment",
            filters=filters,
            or_filters=or_filters,
            fields=["name"]
        )
        total_count = len(total_names)

    except Exception as e:
        frappe.log_error("Error While Getting Shift Assignment List", str(e))
        frappe.clear_messages()
        frappe.local.response["message"] = {
            "success": False,
            "message": f"Error While Getting Shift Assignment List: {str(e)}",
            "data": None,
        }

    else:
        frappe.local.response["message"] = {
            "success": True,
            "message": "Shift Assignments Loaded Successfully!",
            "data": shift_assignment_list,
            "count": total_count        
        }