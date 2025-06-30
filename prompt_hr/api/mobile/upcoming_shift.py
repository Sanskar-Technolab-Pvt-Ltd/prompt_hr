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

        # Parse incoming parameters
        try:
            if filters and str(type(filters)) == "<class 'str'>":
                filters = json.loads(filters)
        except:
            pass
            
        try:
            if or_filters and str(type(or_filters)) == "<class 'str'>":
                or_filters = json.loads(or_filters)
        except:
            pass
            
        try:
            if fields and str(type(fields)) == "<class 'str'>":
                fields = json.loads(fields)
        except:
            pass
        
        # Handle filter format conversion
        processed_filters = {}
        
        if filters:
            if str(type(filters)) == "<class 'list'>" and len(filters) > 0:
                for filter_condition in filters:
                    if str(type(filter_condition)) == "<class 'list'>" and len(filter_condition) >= 3:
                        field_name = filter_condition[0]
                        operator = filter_condition[1]
                        value = filter_condition[2]
                        
                        if operator == "=":
                            processed_filters[field_name] = value
                        else:
                            processed_filters[field_name] = [operator, value]
           
            elif str(type(filters)) == "<class 'dict'>":
                processed_filters = filters.copy()
        
        # Add mandatory conditions
        processed_filters.update({
            "start_date": [">", nowdate()],
            "end_date": ["is", "set"],
            "docstatus": 1
        })

        # Get Shift Assignment List
        shift_assignment_list = frappe.get_list(
            "Shift Assignment",
            filters=processed_filters,
            or_filters=or_filters,
            fields=fields,
            order_by=order_by,
            limit_page_length=limit_page_length,
            limit_start=limit_start,
        )

        # Get total count
        total_names = frappe.get_list(
            "Shift Assignment",
            filters=processed_filters,
            or_filters=or_filters,
            fields=["name"],
            ignore_permissions=False
        )
        total_count = len(total_names)

        frappe.local.response["message"] = {
            "success": True,
            "message": "Shift Assignments Loaded Successfully!",
            "data": shift_assignment_list,
            "count": total_count        
        }

    except Exception as e:
        frappe.log_error("Error While Getting Shift Assignment List", str(e))
        frappe.clear_messages()
        frappe.local.response["message"] = {
            "success": False,
            "message": f"Error While Getting Shift Assignment List: {str(e)}",
            "data": None,
        }
