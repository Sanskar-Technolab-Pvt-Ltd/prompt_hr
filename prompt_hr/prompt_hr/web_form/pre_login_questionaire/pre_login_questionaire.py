import frappe

def get_context(context):
    """BUILD CONTEXT FOR WEB FORM WITH EMPLOYEE PRE-LOGIN QUESTIONNAIRE"""
    user = frappe.session.user
    context.questionnaire_responses = []

    # ? GET EMPLOYEE LINKED TO USER
    employee = frappe.get_value("Employee", {"user_id": user}, "name")
    if not employee:
        return context

    # ? LOAD EMPLOYEE DOC WITH CHILD TABLE
    emp_doc = frappe.get_doc("Employee", employee)

    # ? GET CHILD TABLE RECORDS
    child_table_entries = emp_doc.get("custom_pre_login_questionnaire_response") or []

    # ? TRANSFORM CHILD TABLE INTO FIELDS
    dynamic_fields = []
    for idx, entry in enumerate(child_table_entries, start=1):
        fieldtype = entry.field_type or "Data"
        options = None

        # ? IF FIELD IS LINK OR SELECT, GET THE LINKED OPTIONS
        if fieldtype in ["Link", "Select"]:
            options_value = frappe.db.get_value(
                "DocField",
                {"parent": "Employee", "fieldname": entry.employee_field_name},
                "options"
            ) or frappe.db.get_value(
                "Custom Field",
                {"dt": "Employee", "fieldname": entry.employee_field_name},
                "options"
            )
            if options_value:
                options = options_value  # ONLY SET IF EXISTS

        # ? IF FIELD IS AUTOCOMPLETE, GET OPTIONS
        elif fieldtype == "Autocomplete":
            options_value = make_autocomplete_options(entry.employee_field_name)
            if options_value:
                options = options_value  # ONLY SET IF EXISTS
    
        dynamic_fields.append({
            "fieldname": entry.employee_field_name,
            "label": entry.field_label,                            # FIELD LABEL
            "fieldtype": fieldtype,                                # FIELD TYPE
            "default": entry.employee_response,                    # PREFILLED RESPONSE
            "read_only": 1 if entry.status == "Approve" else 0,   # READONLY FLAG
            # ? ONLY ADD OPTIONS IF THEY EXIST
            **({"options": options} if options else {})
        })

    print(dynamic_fields)
    # ? ATTACH FIELDS INTO WEB FORM DOC
    if hasattr(context, 'web_form_doc'):
        if not context.web_form_doc.get("web_form_fields"):
            context.web_form_doc["web_form_fields"] = []
        context.web_form_doc["web_form_fields"].extend(dynamic_fields)

    # ? ALSO STORE RAW RESPONSES IF YOU NEED
    context.questionnaire_responses = dynamic_fields

    return context


@frappe.whitelist()
def make_autocomplete_options(fieldname, searchtxt=None):
    #? GET THE DOCTYPE LINKED TO THIS FIELD
    doctype = frappe.db.get_value(
                "DocField",
                {"parent": "Employee", "fieldname": fieldname},
                "options"
            ) or frappe.db.get_value(
                "Custom Field",
                {"dt": "Employee", "fieldname": fieldname},
                "options"
            )
    
    if not doctype:
        return []

    #? BUILD FILTER
    filters = {}
    if searchtxt:
        filters["name"] = ["like", f"%{searchtxt}%"]

    #? GET MATCHING RECORDS
    options = frappe.get_all(
        doctype,
        fields=["name"],
        filters=filters,
        order_by="name asc",
        limit_page_length=20,
        pluck="name"
    )
    return options
