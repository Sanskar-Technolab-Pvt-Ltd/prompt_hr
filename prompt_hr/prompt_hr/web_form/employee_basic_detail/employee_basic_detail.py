import frappe

def get_context(context):
    """Prepare dynamic fields and set list columns for the Employee Web Form"""
    hr_settings = frappe.get_single("HR Settings")
    dynamic_fields = []

    # Collect custom fields from HR Settings
    for field in getattr(hr_settings, "custom_employee_basic_detail_fields", []) or []:
        if field.employee_field_name:
            field_meta = frappe.get_meta("Employee").get_field(field.employee_field_name)
            dynamic_fields.append({
                "fieldname": field.employee_field_name,
                "label": field.field_label,
                "fieldtype": field_meta.fieldtype if field_meta else "Data"
            })

    # If called in a Web Form context, set the list columns
    if hasattr(context, "web_form_doc"):
        context.web_form_doc["list_columns"] = dynamic_fields


def get_list_context(context):
    """Attach custom list function for Employee Web Form"""
    return {"get_list": custom_employee_list}


def custom_employee_list(**kwargs):
    """Fetch Employee list dynamically with fields from HR Settings,
    ignoring permissions but filtering only allowed kwargs
    """
    hr_settings = frappe.get_single("HR Settings")
    field_names = ["name"]

    # Add configured fields
    for field in getattr(hr_settings, "custom_employee_basic_detail_fields", []) or []:
        if field.employee_field_name:
            field_names.append(field.employee_field_name)

    # Whitelist allowed keys for get_all
    allowed_keys = {"filters", "fields", "order_by", "limit_start", "limit_page_length", "ignore_permissions"}
    filtered_kwargs = {k: v for k, v in kwargs.items() if k in allowed_keys}

    # Default to ignoring permissions
    filtered_kwargs.setdefault("ignore_permissions", True)
    filtered_kwargs["fields"] = field_names

    return frappe.get_all("Employee", **filtered_kwargs)
