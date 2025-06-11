import frappe
from hrms.hr.doctype.leave_policy_assignment.leave_policy_assignment import (
    LeavePolicyAssignment,
)
from frappe import _, bold
from frappe.utils import formatdate, getdate


class CustomLeavePolicyAssignment(LeavePolicyAssignment):
    def on_submit(self):
        """
        Triggered after a Leave Policy Assignment document is submitted.
        Allocates leaves based on policy details, effective dates, and current date.
        Updates corresponding Leave Allocation and Leave Ledger Entry records.
        """
        super().on_submit()
        effective_from = self.effective_from
        effective_to = self.effective_to

        if not effective_from or not effective_to:
            frappe.throw(
                "Effective From or Effective To date is missing in the document."
            )

        # Fetch all relevant Leave Allocations for this assignment
        leave_allocations = frappe.db.get_all(
            "Leave Allocation",
            filters={"employee": self.employee, "leave_policy_assignment": self.name},
            fields=["name", "leave_type", "unused_leaves"],
        )

        if not leave_allocations:
            frappe.throw("No Leave Allocation records found for this assignment.")

        current_date = frappe.utils.nowdate()

        leave_policy_doc = frappe.get_doc("Leave Policy", self.leave_policy)

        for leave_policy_detail in leave_policy_doc.get("leave_policy_details"):
            leave_type = leave_policy_detail.leave_type
            annual_allocation = leave_policy_detail.annual_allocation

            # Fetch Leave Type details
            leave_type_doc = frappe.get_doc("Leave Type", leave_type)
            is_earned = leave_type_doc.custom_is_earned_leave_allocation
            is_quarterly = leave_type_doc.custom_is_quarterly_carryforward_rule_applied
            allocation_day = leave_type_doc.allocate_on_day

            # Check if Maternity Leave Application is Present on Curernt Date
            is_maternity_leave = 0
            leave_applications = frappe.get_all(
                "Leave Application",
                filters={
                    "employee": self.employee,
                    "company": self.company,
                    "docstatus": 1,
                },
                fields=["name", "leave_type", "from_date", "to_date"],
            )
            for leave_application in leave_applications:
                leave_type_app = frappe.get_doc(
                    "Leave Type", leave_application.leave_type
                )
                if leave_type_app.custom_is_maternity_leave:
                    if (getdate(current_date) >= leave_application.from_date) and (
                        getdate(current_date) <= leave_application.to_date
                    ):
                        is_maternity_leave = 1
                        break

            if is_earned and is_quarterly:
                # Quarterly allocation logic
                quarters = []
                for i in range(4):
                    start = frappe.utils.add_months(effective_from, i * 3)
                    end = frappe.utils.add_days(frappe.utils.add_months(start, 3), -1)
                    quarters.append((start, end))

                leave_per_quarter = annual_allocation / 4
                passed_quarters = 0

                for start, end in quarters:
                    if allocation_day == "First Day" and frappe.utils.getdate(
                        start
                    ) <= frappe.utils.getdate(current_date):
                        passed_quarters += 1
                    elif allocation_day == "Last Day" and frappe.utils.getdate(
                        end
                    ) <= frappe.utils.getdate(current_date):
                        passed_quarters += 1

                allocated_leaves = passed_quarters * leave_per_quarter

                # Allocated 0 Earned Leaves if Maternity Leave Application is Confirmed.
                if is_maternity_leave:
                    allocated_leaves = 0
                
                # Update Leave Allocation and Ledger Entry
                for alloc in leave_allocations:
                    if alloc.leave_type == leave_type:
                        total_allocated = allocated_leaves + (alloc.unused_leaves or 0)
                        frappe.db.set_value(
                            "Leave Allocation",
                            alloc.name,
                            "new_leaves_allocated",
                            allocated_leaves,
                        )
                        frappe.db.set_value(
                            "Leave Allocation",
                            alloc.name,
                            "total_leaves_allocated",
                            total_allocated,
                        )

                        ledger_name = frappe.db.get_value(
                            "Leave Ledger Entry",
                            {"transaction_name": alloc.name, "is_carry_forward": 0},
                            "name",
                        )
                        if ledger_name:
                            frappe.db.set_value(
                                "Leave Ledger Entry",
                                ledger_name,
                                "leaves",
                                allocated_leaves,
                            )
            # Update Monthly Earned Leave Allocation if Employee is on Maternity Leave on That Day
            elif is_maternity_leave and is_earned and leave_type_doc.is_earned_leave:
                for alloc in leave_allocations:
                    if alloc.leave_type == leave_type:
                        total_allocated = alloc.unused_leaves or 0
                        frappe.db.set_value(
                            "Leave Allocation",
                            alloc.name,
                            "new_leaves_allocated",
                            0,
                        )
                        frappe.db.set_value(
                            "Leave Allocation",
                            alloc.name,
                            "total_leaves_allocated",
                            total_allocated,
                        )

                        ledger_name = frappe.db.get_value(
                            "Leave Ledger Entry",
                            {"transaction_name": alloc.name, "is_carry_forward": 0},
                            "name",
                        )
                        if ledger_name:
                            frappe.db.set_value(
                                "Leave Ledger Entry",
                                ledger_name,
                                "leaves",
                                0,
                            )
                

        frappe.db.commit()

    def validate_policy_assignment_overlap(self):
        # Get all overlapping leave policy assignments for this employee
        overlapping_assignments = frappe.get_all(
            "Leave Policy Assignment",
            filters={
                "employee": self.employee,
                "name": ["!=", self.name],
                "docstatus": 1,
                "effective_to": [">=", self.effective_from],
                "effective_from": ["<=", self.effective_to],
            },
            fields=["name", "leave_policy"],
        )
        policy_details = frappe.get_all(
                "Leave Policy Detail",
                filters={"parent": self.leave_policy},
                fields=["leave_type"],
            )

        for detail in policy_details:
            leave_type = frappe.get_doc("Leave Type", detail.leave_type)
            # Skip Valdiation for Paternity/Maternity Leave
            if (
                leave_type.custom_is_maternity_leave
                or leave_type.custom_is_paternity_leave
            ):
                return
            
        for assignment in overlapping_assignments:
            # Fetch leave types in the overlapping assignment
            policy_details = frappe.get_all(
                "Leave Policy Detail",
                filters={"parent": assignment.leave_policy},
                fields=["leave_type"],
            )

            for detail in policy_details:
                leave_type = frappe.get_doc("Leave Type", detail.leave_type)
                # If any non-maternity/paternity leave exists → throw error
                if not (
                    leave_type.custom_is_maternity_leave
                    or leave_type.custom_is_paternity_leave
                ):
                    frappe.throw(
                        _(
                            "Leave Policy: {0} already assigned for Employee {1} for period {2} to {3}"
                        ).format(
                            bold(assignment.leave_policy),
                            bold(self.employee),
                            bold(formatdate(self.effective_from)),
                            bold(formatdate(self.effective_to)),
                        ),
                        title=_("Leave Policy Assignment Overlap"),
                    )


@frappe.whitelist()
def filter_leave_policy_for_display(
    doctype, txt, searchfield, start, page_len, filters
):
    gender = filters.get("gender")
    company = filters.get("company")

    leave_policies = frappe.get_all(
        "Leave Policy", filters={"custom_company": company}, fields=["name", "title"]
    )
    leave_policy_display = []

    for policy in leave_policies:
        leave_types = frappe.get_all(
            "Leave Policy Detail",
            filters={"parent": policy.name},
            fields=["leave_type"],
        )
        leave_type_names = [lt.leave_type for lt in leave_types]
        if not leave_type_names:
            leave_policy_display.append((policy.name, policy.title))
            continue

        leave_type_docs = frappe.get_all(
            "Leave Type",
            filters={"name": ["in", leave_type_names]},
            fields=["name", "custom_is_paternity_leave", "custom_is_maternity_leave"],
        )

        exclude = False
        for lt in leave_type_docs:
            if gender == "Male" and lt.custom_is_maternity_leave:
                exclude = True
                break
            if gender == "Female" and lt.custom_is_paternity_leave:
                exclude = True
                break

        if not exclude:
            leave_policy_display.append((policy.name, policy.title))

    return leave_policy_display
