import frappe
from prompt_hr.py.employee import get_employee_doctype_fields

def set_employee_field_names(doc, event):
    
    emp_fields = get_employee_doctype_fields()
    if doc.custom_penalization_criteria_table_for_prompt:
        for row in doc.custom_penalization_criteria_table_for_prompt:
            if row.employee_field and not row.employee_field_name:
                for field in emp_fields:
                    if row.employee_field == field.get("label"):
                        row.employee_field_name = field.get("fieldname")
                        break
            