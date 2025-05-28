import frappe
from frappe import _, bold
from frappe.utils import get_link_to_form, cint
from prompt_hr.py.leave_allocation import get_matching_link_field


def before_save(doc, method=None):
    if cint(doc.actual_encashable_days) == 0:
        frappe.throw(_("Encashment failed: You have zero encashable days available."))
