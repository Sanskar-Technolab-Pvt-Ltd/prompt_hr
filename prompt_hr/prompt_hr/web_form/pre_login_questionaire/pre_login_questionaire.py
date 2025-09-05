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

    # ? TRANSFORM CHILD TABLE INTO LIST OF DICTS WITH KEY-VALUE PAIRS
    transformed_responses = []
    for entry in child_table_entries:
        transformed_responses.append({
            "field_label": entry.field_label,
            "field_type": entry.field_type,
            "status": entry.status,
            "response": entry.employee_response
        })

    # ? SET TRANSFORMED DATA INTO CONTEXT
    context.questionnaire_responses = transformed_responses

    if hasattr(context, 'web_form_doc'):  
        context.web_form_doc['questionnaire_responses'] = context.questionnaire_responses
