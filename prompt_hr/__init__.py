__version__ = "0.0.1"


import frappe
from typing import List
import hrms.hr.doctype.interview_feedback.interview_feedback as interview_feedback_module
import hrms.hr.doctype.interview.interview as interview_module
from hrms.hr.doctype.leave_policy_assignment.leave_policy_assignment import LeavePolicyAssignment
from prompt_hr.overrides.leave_policy_assignment_override import custom_calculate_pro_rated_leaves

from hrms.hr.doctype.leave_policy_assignment import leave_policy_assignment
from prompt_hr.overrides.leave_policy_assignment_override import is_earned_leave_applicable_for_current_month, custom_calculate_pro_rated_leaves

leave_policy_assignment.calculate_pro_rated_leaves = custom_calculate_pro_rated_leaves

import hrms.hr.utils
import hrms.hr.doctype.leave_application.leave_application as leave_application_module
import hrms.hr.report.employee_leave_balance.employee_leave_balance as leave_balance_report
from frappe.model import workflow
from hrms.hr.doctype.leave_allocation.leave_allocation import LeaveAllocation
from hrms.hr.doctype.leave_encashment.leave_encashment import LeaveEncashment
from prompt_hr.overrides.workflow_override import custom_get_transitions, custom_has_approval_access
from prompt_hr.py.leave_allocation import custom_set_total_leaves_allocated
from prompt_hr.py.leave_encashment import custom_set_actual_encashable_days, custom_set_encashment_amount
from prompt_hr.py.leave_application import custom_get_number_of_leave_days, custom_update_previous_leave_allocation, custom_check_effective_date, custom_get_leave_details, custom_get_allocated_and_expired_leaves, custom_get_opening_balance, custom_get_data, custom_get_leave_balance_on, custom_get_columns
from hrms.payroll.doctype.payroll_entry import payroll_entry 
from prompt_hr.py.salary_slip_overriden_methods import custom_create_salary_slips_for_employees
from hrms.hr.doctype.job_requisition import job_requisition
from prompt_hr.py import job_requisition_overriden_class 
from hrms.hr.doctype.full_and_final_statement.full_and_final_statement import FullandFinalStatement
from prompt_hr.py import full_and_final_statement
from prompt_hr.py.leave_type import custom_get_earned_leaves
import hrms.payroll.doctype.payroll_entry.payroll_entry as PayrollEntryModule
from prompt_hr.overrides.payroll_entry_override import custom_set_filter_conditions

PayrollEntryModule.set_filter_conditions = custom_set_filter_conditions
from prompt_hr.py.utils import calculate_annual_eligible_hra_exemption, get_component_amt_from_salary_slip
import hrms.regional.india.utils as hra_override
hra_override.calculate_annual_eligible_hra_exemption = calculate_annual_eligible_hra_exemption
hra_override.get_component_amt_from_salary_slip = get_component_amt_from_salary_slip
import lending.loan_management.doctype.loan_repayment.loan_repayment as LoanRepayment
import hrms.payroll.doctype.salary_slip.salary_slip_loan_utils as LoanUtils
from prompt_hr.py.loan_application import custom_get_accrued_interest_entries, custom_process_loan_interest_accruals

LoanRepayment.get_accrued_interest_entries = custom_get_accrued_interest_entries

LoanUtils.process_loan_interest_accruals = custom_process_loan_interest_accruals


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
        fields=["custom_user", "user_name", "is_confirm", "name"]
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
        if interviewer.get("custom_user"):
            supplier = frappe.get_doc("Supplier", interviewer.custom_user)
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
leave_application_module.get_leave_balance_on = custom_get_leave_balance_on
leave_application_module.get_leave_details = custom_get_leave_details
leave_application_module.get_number_of_leave_days = custom_get_number_of_leave_days
leave_balance_report.get_allocated_and_expired_leaves = custom_get_allocated_and_expired_leaves
leave_balance_report.get_opening_balance = custom_get_opening_balance
leave_balance_report.get_columns = custom_get_columns
leave_balance_report.get_data = custom_get_data
LeaveAllocation.set_total_leaves_allocated = custom_set_total_leaves_allocated
LeaveEncashment.set_actual_encashable_days = custom_set_actual_encashable_days
LeaveEncashment.set_encashment_amount = custom_set_encashment_amount
payroll_entry.create_salary_slips_for_employees = custom_create_salary_slips_for_employees
job_requisition.JobRequisition = job_requisition_overriden_class.JobRequisition
FullandFinalStatement.get_payable_component = full_and_final_statement.custom_get_payable_component
FullandFinalStatement.create_component_row = full_and_final_statement.custom_create_component_row
FullandFinalStatement.get_receivable_component = full_and_final_statement.custom_get_receivable_component
hrms.hr.utils.get_earned_leaves = custom_get_earned_leaves
leave_policy_assignment.is_earned_leave_applicable_for_current_month = is_earned_leave_applicable_for_current_month
