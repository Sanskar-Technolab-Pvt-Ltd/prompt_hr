import frappe
from prompt_hr.py.appointment_letter import set_annexure_details

def before_save(doc, method=None):
    doc.custom_employee = doc.employee
    set_annexure_details(doc)