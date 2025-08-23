import frappe
from frappe import _
from hrms.hr.doctype.leave_encashment.leave_encashment import LeaveEncashment
from hrms.hr.doctype.leave_application.leave_application import get_leaves_for_period

class CustomLeaveEncashment(LeaveEncashment):
    def set_leave_balance(self):
        allocation = self.get_leave_allocation()
        if not allocation:
            frappe.throw(
                _("No Leaves Allocated to Employee: {0} for Leave Type: {1}").format(
                    self.employee, self.leave_type
                )
            )

        self.leave_balance = (
            allocation.total_leaves_allocated
            - allocation.carry_forwarded_leaves_count
            # adding this because the function returns a -ve number
            + get_leaves_for_period(
                self.employee, self.leave_type, allocation.from_date, self.encashment_date
            )
            - get_negative_leave_allocation(
                self.employee, self.leave_type, allocation.from_date, self.encashment_date
            )
        )

        self.leave_allocation = allocation.name


def get_negative_leave_allocation(employee, leave_type, from_date, to_date):
    negative_leaves = frappe.db.sql(
        """
        SELECT
            employee, leave_type, from_date, to_date, leaves, transaction_name, transaction_type, holiday_list,
            is_carry_forward, is_expired
        FROM `tabLeave Ledger Entry`
        WHERE employee=%(employee)s AND leave_type=%(leave_type)s
            AND docstatus=1
            AND (leaves<0
                OR is_expired=1)
            AND transaction_type = %(transaction_type)s
            AND (from_date between %(from_date)s AND %(to_date)s
                OR to_date between %(from_date)s AND %(to_date)s
                OR (from_date < %(from_date)s AND to_date > %(to_date)s))
    """,
        {"from_date": from_date, "to_date": to_date, "employee": employee, "leave_type": leave_type, "transaction_type": "Leave Allocation"},
        as_dict=1,
    )

    leaves = 0
    for entry in negative_leaves:
        leaves += entry.leaves

    return abs(leaves)
