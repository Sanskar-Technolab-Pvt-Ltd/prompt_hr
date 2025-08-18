import frappe
from frappe.utils import getdate, today, flt
from frappe import _
from hrms.hr.doctype.leave_application.leave_application import LeaveApplication, get_leave_period, is_lwp
from prompt_hr.py.leave_application import custom_get_number_of_leave_days


class CustomLeaveApplication(LeaveApplication):
    def validate_balance_leaves(self):
        if not self.leave_type:
            return

        is_compensatory = frappe.db.get_value("Leave Type", self.leave_type, "is_compensatory")
        if not is_compensatory:
            return super().validate_balance_leaves()

        #! FETCH LEAVE PERIOD RANGE
        leave_periods = get_leave_period(self.from_date, self.to_date, self.company)
        if leave_periods:
            leaves_start_date = leave_periods[0].get("from_date")
            leaves_end_date = leave_periods[0].get("to_date")
        else:
            #! DEFAULT TO JANUARY 1 IF LEAVE PERIOD NOT DEFINED
            year = getdate(self.from_date).year if self.from_date else today().year
            leaves_start_date = getdate(f"{year}-01-01")
            leaves_end_date = getdate(f"{year}-12-31")

        #! VALIDATE DATE RANGE AND CALCULATE TOTAL LEAVE DAYS
        if not (self.from_date and self.to_date):
            return super().validate_balance_leaves()

        self.total_leave_days = custom_get_number_of_leave_days(
            self.employee,
            self.leave_type,
            self.from_date,
            self.to_date,
            self.half_day,
            self.half_day_date,
        )

        if self.total_leave_days <= 0:
            frappe.throw(_("The day(s) on which you are applying for leave are holidays. You need not apply for leave."))

        #! SKIP IF LEAVE TYPE IS LWP
        if is_lwp(self.leave_type):
            return

        #! FETCH ALL COMP OFF ALLOCATIONS
        comp_off_allocations = frappe.get_all(
            "Leave Ledger Entry",
            filters={
                "employee": self.employee,
                "leave_type": self.leave_type,
                "docstatus": 1,
                "from_date": (">=", leaves_start_date),
                "from_date": ("<=", self.from_date),
                "transaction_type": "Leave Allocation",
                "leaves": (">", 0)
            },
            fields=["name", "leaves", "from_date", "to_date"],
            order_by="from_date asc"
        )

        #? BUILD A POOL OF ALLOCATED LEAVES
        allocation_pool = [{
            "name": alloc.name,
            "from_date": getdate(alloc.from_date),
            "to_date": getdate(alloc.to_date),
            "available": flt(alloc.leaves)
        } for alloc in comp_off_allocations]

        #! FETCH USED LEAVES BEFORE FROM_DATE
        leaves_taken = frappe.get_all(
            "Leave Ledger Entry",
            filters={
                "employee": self.employee,
                "leave_type": self.leave_type,
                "docstatus": 1,
                "leaves": ("<", 0),
                "from_date": (">=", leaves_start_date),
                "to_date": ("<=", leaves_end_date),
                "transaction_type": "Leave Application"
            },
            fields=["name", "leaves", "from_date", "to_date"],
            order_by="from_date asc"
        )
        #! FETCH ALL NEGATIVE COMP OFF ALLOCATIONS
        negative_allocations = frappe.get_all(
            "Leave Ledger Entry",
            filters={
                "employee": self.employee,
                "leave_type": self.leave_type,
                "docstatus": 1,
                "from_date": (">=", leaves_start_date),
                "from_date": ("<=", self.from_date),
                "transaction_type": "Leave Allocation",
                "leaves": ("<", 0)
            },
            fields=["name", "leaves", "from_date", "to_date"],
            order_by="from_date asc"
        )
        #? DEDUCT USED LEAVES AND EXPIRED LEAVES FROM ALLOCATED POOL
        for used in leaves_taken+negative_allocations:
            leave_days = abs(flt(used.leaves))
            leave_from = getdate(used.from_date)
            leave_to = getdate(used.to_date)

            for alloc in allocation_pool:
                if alloc["available"] <= 0:
                    continue

                #? CHECK OVERLAPPING PERIOD
                if (
                    alloc["from_date"] <= leave_from <= alloc["to_date"]
                    or alloc["from_date"] <= leave_to <= alloc["to_date"]
                ):
                    consumed = min(leave_days, alloc["available"])
                    alloc["available"] -= consumed
                    leave_days -= consumed

                if leave_days <= 0:
                    break

        #! CALCULATE REMAINING BALANCE AFTER DEDUCTIONS
        remaining_leaves = sum(
            alloc["available"]
            for alloc in allocation_pool
            if alloc["to_date"] >= getdate(self.from_date)
        )
        if not remaining_leaves or self.total_leave_days > remaining_leaves:
            self.show_insufficient_balance_message(remaining_leaves)
