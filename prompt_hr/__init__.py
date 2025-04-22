__version__ = "0.0.1"

import frappe
from typing import List
import hrms.hr.doctype.interview_feedback.interview_feedback as interview_feedback_module

@frappe.whitelist()
def custom_get_applicable_interviewers(interview: str) -> List[str]:
    interviewers = frappe.get_all(
        "Interview Detail",
        filters={"parent": interview},
        fields=["custom_interviewer_employee", "custom_interviewer_name", "custom_is_confirm", "name"]
    )
    external_interviewers = frappe.get_all(
        "External Interviewer",
        filters={"parent": interview},
        fields=["user", "user_name", "is_confirm", "name"]
    )
    users = []
    for interviewer in interviewers:
        if interviewer.custom_interviewer_employee:
            employee = frappe.get_doc("Employee", interviewer.custom_interviewer_employee)
            if employee.user_id:
                user = frappe.get_doc("User", employee.user_id)
                if user and user.enabled and user.name not in users:
                    users.append(user.name)
    for interviewer in external_interviewers:
        if interviewer.get("user"):
            supplier = frappe.get_doc("Supplier", interviewer.user)
            if supplier.custom_user:
                user = frappe.get_doc("User", supplier.custom_user)
                if user and user.enabled and user.name not in users:
                    users.append(user.name)

    return users

# Override original function
interview_feedback_module.get_applicable_interviewers = custom_get_applicable_interviewers

from frappe.model import workflow
from prompt_hr.overrides.workflow_override import custom_get_transitions, custom_has_approval_access




workflow.has_approval_access = custom_has_approval_access
workflow.get_transitions = custom_get_transitions

