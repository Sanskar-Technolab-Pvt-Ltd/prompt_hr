import frappe

@frappe.whitelist()
def create(**args):
    try:
        # ? DEFINE MANDATORY FIELDS
        mandatory_fields = {
            "title": "Title",
            "message": "Message",
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

        frappe.log_error(
        message=args.get("message"),
        title=args.get("title")
        )

        
    except Exception as e:
        # ? HANDLE ERRORS
        frappe.log_error("While Creating Error Log", frappe.get_traceback())
        frappe.clear_messages()
        frappe.local.response["message"] = {
            "success": False,
            "message": f"While Creating Error Log: {str(e)}",
           
        }

    else:
        # ? HANDLE SUCCESS
        frappe.local.response["message"] = {
            "success": True,
            "message": "Error Log Created Successfully!",
        }