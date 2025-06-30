import frappe
from hrms.hr.doctype.leave_allocation.leave_allocation import LeaveAllocation
from frappe.utils import flt
from frappe import _
from hrms.hr.doctype.leave_allocation.leave_allocation import get_carry_forwarded_leaves
from prompt_hr.py.leave_allocation import check_carry_forward_criteria

class CustomLeaveAllocation(LeaveAllocation):
    @frappe.whitelist()
    def set_total_leaves_allocated(self):
        self.unused_leaves = flt(
            get_carry_forwarded_leaves(self.employee, self.leave_type, self.from_date, self.carry_forward),
            self.precision("unused_leaves"),
        )
        if self.carry_forward:
            employee_doc = frappe.get_doc("Employee", self.employee)
            leave_type = frappe.get_doc("Leave Type", self.leave_type)
            if self.unused_leaves > check_carry_forward_criteria(employee_doc, leave_type):
                self.unused_leaves =  check_carry_forward_criteria(employee_doc, leave_type)
            elif leave_type.custom_maximum_ctc_limit_for_carry_forward:
                if employee_doc.ctc > leave_type.custom_maximum_ctc_limit_for_carry_forward:
                    self.unused_leaves =  min(self.unused_leaves,leave_type.maximum_carry_forwarded_leaves)

        self.total_leaves_allocated = flt(
            flt(self.unused_leaves) + flt(self.new_leaves_allocated),
            self.precision("total_leaves_allocated"),
        )

        self.limit_carry_forward_based_on_max_allowed_leaves()

        if self.carry_forward:
            self.set_carry_forwarded_leaves_in_previous_allocation()

        if (
            not self.total_leaves_allocated
            and not frappe.db.get_value("Leave Type", self.leave_type, "is_earned_leave")
            and not frappe.db.get_value("Leave Type", self.leave_type, "is_compensatory")
        ):
            frappe.throw(_("Total leaves allocated is mandatory for Leave Type {0}").format(self.leave_type))