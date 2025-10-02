import frappe

def get_context(context):
    """Prepare dynamic fields and set list columns for the Employee Web Form"""
    employee_fields = {
        "fieldname": "employee",
        "label": "Employee",                           
        "fieldtype": "Autocomplete",
        "options": make_autocomplete_options_for_employee("employee")
    }
    if hasattr(context, 'web_form_doc'):
        context.web_form_doc["web_form_fields"] = []
        context.web_form_doc["web_form_fields"].append(employee_fields)

@frappe.whitelist()
def get_basic_fields_data(employee):
    """
    RETURN EMPLOYEE DETAILS ON SELECTION
    """

    if not employee:
        return {}

    hr_settings = frappe.get_single("HR Settings")
    dynamic_fields = []
    table_fields = {}
    table_data = {}
    # Collect custom fields from HR Settings
    for field in getattr(hr_settings, "custom_employee_basic_detail_fields", []) or []:
        if field.field_type == "Table":
            table_fields[field.employee_field_name] = None
        else:
            if field.employee_field_name:
                dynamic_fields.append(
                    field.employee_field_name
                )

    if table_fields:
        for field in table_fields:
            doctype_name = frappe.db.get_value(
                "DocField",
                {"parent": "Employee", "fieldname": field},
                "options"
            ) or frappe.db.get_value(
                "Custom Field",
                {"dt": "Employee", "fieldname": field},
                "options"
            )
            if doctype_name:
                meta = frappe.get_meta(doctype_name)
                allowed_fields = [df.fieldname for df in meta.fields if df.fieldname]

                table_data[field] = [frappe.get_all(doctype_name, {"parent": employee}, allowed_fields), doctype_name]
    data = frappe.get_all("Employee", {"name":employee}, dynamic_fields)
    
    # ? GET LABELS FOR EACH FIELD

    data_with_label = {}
    table_data_with_label = {}
    for field, rows in table_data.items():
        table_data_with_label[field] = []
        field_label  = frappe.db.get_value("DocField", {"parent": "Employee", "fieldname": field}, "label") or frappe.db.get_value("Custom Field", {"dt": "Employee", "fieldname": field}, "label")
        for row in rows[0]:
            row_with_label = {}
            for key, value in row.items():
                label = frappe.db.get_value("DocField", {"parent": rows[1], "fieldname": key}, "label") or frappe.db.get_value("Custom Field", {"dt": rows[1], "fieldname": key}, "label")
                row_with_label[key] = [value, label]
            table_data_with_label[field] = [field_label, row_with_label]
    
    for key, value in data[0].items():
        label = frappe.db.get_value("DocField", {"parent": "Employee", "fieldname": key}, "label") or frappe.db.get_value("Custom Field", {"dt": "Employee", "fieldname": key}, "label")
        data_with_label[key] = [value, label]
    
    if not dynamic_fields and not table_fields:
        return {
            "basic_data": {},
            "table_datas": {}
        }
    return {
        "basic_data": data_with_label,
        "table_datas": table_data_with_label
    }


@frappe.whitelist()
def make_autocomplete_options_for_employee(fieldname, searchtxt=None):
    filters = {}
    if searchtxt:
        filters["employee_name"] = ["like", f"%{searchtxt}%"]

    employees = frappe.get_all(
        "Employee",
        fields=["name", "employee_name"],
        filters=filters,
        order_by="name asc",
        limit_page_length=20
    )

    options = [{"label": emp.employee_name, "value": emp.name} for emp in employees]

    return options
