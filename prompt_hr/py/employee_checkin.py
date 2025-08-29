# File: prompt_hr/doctype/employee_checkin/employee_checkin.py
import frappe
from frappe import _
from prompt_hr.py.employee import check_if_employee_create_checkin_is_validate_via_web


def before_insert(doc, method):
    """
    ! HOOK: Before insert of Employee Checkin
    ? Logic:
        - Call validation function
        - If returns 0 → Throw message and stop insert
        - If returns 1 → Allow insert
    """

    # ? Get user_id of the current user
    user_id = frappe.session.user

    # ? Call validation function
    is_allowed = check_if_employee_create_checkin_is_validate_via_web(user_id)

    # ? If not allowed, stop the insert
    if is_allowed == 0:
        frappe.throw(_("You are not allowed to create Check-in. "))
