from typing import List
import frappe
from frappe import _
from frappe.utils import (
    flt,
    cint,
)
from hrms.hr.doctype.leave_application.leave_application import (
    get_leave_allocation_records,
    get_leave_approver,
    get_leave_balance_on,
    get_leaves_for_period,
    get_leaves_pending_approval_for_period,
)


@frappe.whitelist()
def get_expected_skill_set(interview_round):
	return frappe.get_all(
		"Expected Skill Set", filters={"parent": interview_round}, fields=["skill","custom_skill_type","custom_rating_scale"], order_by="idx"
	)

@frappe.whitelist()
def get_applicable_interviewers(interview: str) -> List[str]:
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


@frappe.whitelist()
def get_leave_details(employee, date, for_salary_slip=False):
    allocation_records = get_leave_allocation_records(employee, date)
    leave_allocation = {}
    precision = cint(frappe.db.get_single_value("System Settings", "float_precision")) or 2

    for d in allocation_records:
        allocation = allocation_records.get(d, frappe._dict())
        to_date = date if for_salary_slip else allocation.to_date

        remaining_leaves = get_leave_balance_on(
            employee,
            d,
            date,
            to_date=to_date,
            consider_all_leaves_in_the_allocation_period=False if for_salary_slip else True,
        )

        leave_ledger_entry = frappe.get_all(
            "Leave Ledger Entry",
            filters={
                "employee": employee,
                "leave_type": allocation.leave_type,
                "docstatus": 1,
                "from_date": ["<=", date],
                "leaves": [">", 0],
            },
            fields=["name", "leaves"]
        )

        total_leaves = sum([flt(d.leaves) for d in leave_ledger_entry])
        leaves_taken = get_leaves_for_period(employee, d, allocation.from_date, to_date) * -1
        leaves_pending = get_leaves_pending_approval_for_period(employee, d, allocation.from_date, to_date)
        expired_leaves = total_leaves - (remaining_leaves + leaves_taken)

        leave_allocation[d] = {
            "total_leaves": flt(total_leaves),
            "expired_leaves": flt(expired_leaves, precision) if expired_leaves > 0 else 0,
            "leaves_taken": flt(leaves_taken, precision),
            "leaves_pending_approval": flt(leaves_pending, precision),
            "remaining_leaves": flt(remaining_leaves, precision),
        }

    lwp = frappe.get_list("Leave Type", filters={"is_lwp": 1}, pluck="name")

    return {
        "leave_allocation": leave_allocation,
        "leave_approver": get_leave_approver(employee),
        "lwps": lwp,
    }
