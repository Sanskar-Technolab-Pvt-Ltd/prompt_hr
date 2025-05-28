__version__ = "0.0.1"


import frappe
from typing import List
import hrms.hr.doctype.interview_feedback.interview_feedback as interview_feedback_module
import hrms.hr.doctype.interview.interview as interview_module
import hrms.hr.utils
import hrms.hr.doctype.leave_application.leave_application as leave_application_module
import hrms.hr.report.employee_leave_balance.employee_leave_balance as leave_balance_report
from frappe.model import workflow
from prompt_hr.overrides.workflow_override import custom_get_transitions, custom_has_approval_access
from prompt_hr.py.leave_application import custom_get_number_of_leave_days, custom_update_previous_leave_allocation, custom_check_effective_date, custom_get_leave_details, custom_get_allocated_and_expired_leaves
from hrms.payroll.doctype.payroll_entry import payroll_entry 
from prompt_hr.py.salary_slip_overriden_methods import custom_create_salary_slips_for_employees
from hrms.hr.doctype.job_requisition import job_requisition
from prompt_hr.py import job_requisition_overriden_class 
from prompt_hr.py.leave_type import custom_get_earned_leaves

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


workflow.has_approval_access = custom_has_approval_access
workflow.get_transitions = custom_get_transitions

@frappe.whitelist()

def custom_get_expected_skill_set(interview_round):
	return frappe.get_all(
		"Expected Skill Set", filters={"parent": interview_round}, fields=["skill","custom_skill_type","custom_rating_scale"], order_by="idx"
	)

interview_module.get_expected_skill_set = custom_get_expected_skill_set
hrms.hr.utils.check_effective_date = custom_check_effective_date
hrms.hr.utils.update_previous_leave_allocation = custom_update_previous_leave_allocation
leave_application_module.get_number_of_leave_days = custom_get_number_of_leave_days
leave_application_module.get_leave_details = custom_get_leave_details
leave_balance_report.get_allocated_and_expired_leaves = custom_get_allocated_and_expired_leaves 
payroll_entry.create_salary_slips_for_employees = custom_create_salary_slips_for_employees
job_requisition.JobRequisition = job_requisition_overriden_class.JobRequisition
hrms.hr.utils.get_earned_leaves = custom_get_earned_leaves