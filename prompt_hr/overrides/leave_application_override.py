import frappe
from frappe.utils import getdate, today, flt, time_diff_in_hours, cint, formatdate, get_link_to_form
from frappe import _
from hrms.hr.doctype.leave_application.leave_application import LeaveApplication, get_leave_period, is_lwp, OverlapError, InsufficientLeaveBalanceError
from prompt_hr.py.leave_application import custom_get_number_of_leave_days
from prompt_hr.prompt_hr.doctype.employee_penalty.employee_penalty import cancel_penalties
from datetime import timedelta


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
        if (not remaining_leaves or self.total_leave_days > remaining_leaves) and self.status != "Rejected":
            self.show_insufficient_balance_message(remaining_leaves)

    def validate_attendance(self):
        return

    def create_or_update_attendance(self, attendance_name, date):
        status = (
            "Half Day" if self.half_day_date and getdate(date) == getdate(self.half_day_date) else "On Leave"
        )
        if attendance_name:
            # update existing attendance, change absent to on leave or half day
            doc = frappe.get_doc("Attendance", attendance_name)
            half_day_status = None if status == "On Leave" else "Present"
            half_day_time = None

            if half_day_status:
                half_day_time = self.custom_half_day_time
            
            modify_half_day_status = 1 if doc.status == "Absent" and status == "Half Day" else 0
            if half_day_status:
                # ? FETCH SHIFT ASSIGNMENTS FOR TARGET DATE (INCLUDING OPEN-ENDED)
                shift_assignments = frappe.get_all(
                    "Shift Assignment",
                    filters={
                        "employee": doc.employee,
                        "docstatus": 1,
                        "start_date": ["<=", doc.attendance_date],
                    },
                    or_filters=[{"end_date": [">=", doc.attendance_date]}, {"end_date": ["is", "not set"]}],
                    fields=["employee", "shift_type"],
                )

                if shift_assignments:
                    # ? GET SHIFT TYPE FOR TARGET DATE
                    shift_type = shift_assignments[0].shift_type

                    # ? GET SHIFT DETAILS
                    shift_absent_threshold = frappe.db.get_value(
                        "Shift Type", shift_type, "working_hours_threshold_for_absent"
                    )

                    if doc.working_hours and doc.working_hours < shift_absent_threshold:
                        # ? SET HALF DAY STATUS TO ABSENT
                        half_day_status = "Absent"
                        modify_half_day_status = 0
                        status = "Absent"

                    elif not doc.working_hours:
                        if doc.custom_checkin_time and doc.custom_checkout_time:
                            time_diff = time_diff_in_hours(doc.custom_checkout_time,doc.custom_checkin_time)
                            if time_diff < shift_absent_threshold:
                                half_day_status = "Absent"
                                modify_half_day_status = 0
                                status = "Absent"

                        else:
                            half_day_status = "Absent"
                            modify_half_day_status = 0
                            status = "Absent"

            if doc.custom_employee_penalty_id:
                cancel_penalties([doc.custom_employee_penalty_id])

            doc.db_set(
                {
                    "status": status,
                    "leave_type": self.leave_type,
                    "leave_application": self.name,
                    "half_day_status": half_day_status,
                    "modify_half_day_status": modify_half_day_status,
                    "custom_half_day_time": half_day_time
                }
            )
        else:
            # make new attendance and submit it
            doc = frappe.new_doc("Attendance")
            doc.employee = self.employee
            doc.employee_name = self.employee_name
            doc.attendance_date = date
            doc.company = self.company
            doc.leave_type = self.leave_type
            doc.leave_application = self.name
            doc.status = status
            doc.half_day_status = "Present" if status == "Half Day" else None
            doc.modify_half_day_status = 1 if status == "Half Day" else 0
            doc.flags.ignore_validate = True  # ignores check leave record validation in attendance
            doc.insert(ignore_permissions=True)
            doc.submit()


    def validate_leave_overlap(self):
        #! HACK! ENSURE NAME IS NOT NULL TO AVOID PROBLEMS WITH != IN SQL
        if not self.name:
            self.name = "New Leave Application"

        #! FETCH EXISTING LEAVE APPLICATIONS THAT OVERLAP DATE RANGE
        for d in frappe.db.sql(
            """
            SELECT
                name, leave_type, posting_date, from_date, to_date,
                total_leave_days, half_day_date, custom_half_day_time
            FROM `tabLeave Application`
            WHERE employee = %(employee)s
                AND docstatus < 2
                AND status IN ('Open', 'Approved')
                AND to_date >= %(from_date)s
                AND from_date <= %(to_date)s
                AND name != %(name)s
            """,
            {
                "employee": self.employee,
                "from_date": self.from_date,
                "to_date": self.to_date,
                "name": self.name,
            },
            as_dict=1,
        ):
            #? CHECK IF CURRENT APPLICATION IS HALF DAY
            if (
                cint(self.half_day) == 1
                and getdate(self.half_day_date) == getdate(d.half_day_date)
                and (
                    flt(self.total_leave_days) == 0.5
                    or getdate(self.from_date) == getdate(d.to_date)
                    or getdate(self.to_date) == getdate(d.from_date)
                )
            ):
                #? ENSURE NO DUPLICATE HALF-DAY TIME (FIRST/SECOND) FOR SAME DATE
                if (
                    self.custom_half_day_time
                    and d.custom_half_day_time
                    and self.custom_half_day_time.lower() == d.custom_half_day_time.lower()
                ):
                    #! THROW ERROR IF SAME HALF-DAY TIME ALREADY APPLIED
                    self.throw_overlap_error(d)

                total_leaves_on_half_day = self.get_total_leaves_on_half_day()
                if total_leaves_on_half_day >= 1:
                    self.throw_overlap_error(d)
            else:
                #! FULL DAY OR OTHER OVERLAP
                self.throw_overlap_error(d)

    
    def show_insufficient_balance_message(self, leave_balance_for_consumption: float) -> None:
        alloc_on_from_date, alloc_on_to_date = self.get_allocation_based_on_application_dates()

        if frappe.db.get_value("Leave Type", self.leave_type, "allow_negative"):
            if leave_balance_for_consumption != self.leave_balance:
                msg = _("Warning: Insufficient leave balance for Leave Type {0} in this allocation.").format(
                    frappe.bold(self.leave_type)
                )
                msg += "<br><br>"
                msg += _(
                    "Actual balances aren't available because the leave application spans over different leave allocations. "
                    "You can still apply for leaves which would be compensated during the next allocation."
                )
            else:
                msg = _("Warning: Insufficient leave balance for Leave Type {0}.").format(
                    frappe.bold(self.leave_type)
                )

            frappe.msgprint(msg, title=_("Warning"), indicator="orange")
        else:
            if self.is_new() or self.workflow_state == "Pending":
                frappe.throw(
                    _("Insufficient leave balance for Leave Type {0}").format(frappe.bold(self.leave_type)),
                    exc=InsufficientLeaveBalanceError,
                    title=_("Insufficient Balance"),
                )
            elif self.workflow_state == "Approved" or self.workflow_state == 'Approved by Reporting Manager':
                frappe.throw(
                    _("No leave balance available. Please reject this leave application and ask the employee to reapply"),
                    exc=InsufficientLeaveBalanceError,
                    title=_("Leave balance Error"),
                )
