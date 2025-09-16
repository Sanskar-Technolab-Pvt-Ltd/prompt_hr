import frappe
from frappe import _
from frappe.utils import getdate, date_diff, add_days, format_date, add_to_date, today
from hrms.hr.doctype.attendance_request.attendance_request import AttendanceRequest
from hrms.hr.utils import validate_active_employee, validate_dates

class CustomAttendanceRequest(AttendanceRequest):
    def before_insert(self):
        # ? MAKE CUSTOM STATUS PENDING AS WHILE AMENDING IS REMAIN THE PREVIOUS STATUS
        self.custom_status = "Pending"
        self.custom_auto_approve = 0


    def before_validate(self):
        if self.workflow_state == "Approved":
            self.custom_status = "Approved"

        elif self.workflow_state == "Rejected":
            self.custom_status = "Rejected"

    def after_insert(self):
        # === SAFE PARSING ===
        if not self.from_date or not self.to_date:
            frappe.msgprint("From Date and To Date are mandatory for Attendance Request.")
            return

        from_date = getdate(self.from_date)
        to_date = getdate(self.to_date)
        today = getdate()
        # === EDGE CASE: FROM > TO ===
        if from_date > to_date:
            frappe.throw("From Date cannot be after To Date.")

        # === MAIN LOGIC: ONLY SWITCH IF TODAY FALLS IN RANGE ===
        if from_date <= today <= to_date:
            if self.reason in ["On Duty", "Work From Home"]:
                frappe.db.set_value(
                    "Employee",
                    self.employee,
                    "custom_attendance_capture_scheme",
                    "Mobile-Web Checkin-Checkout",
                )

    def validate(self):
        validate_active_employee(self.employee)
        validate_dates(self, self.from_date, self.to_date, False)
        self.validate_half_day()
        self.validate_request_overlap()

        if self.custom_status == "Pending":
            self.validate_no_attendance_to_create()
            attendance_exists = get_existing_attendance(self.employee, self.from_date, self.to_date)
            if attendance_exists:
                buffer_days_for_back_dated_attendance_request = frappe.db.get_single_value(
                    "HR Settings", "custom_maximum_days_for_backdated_attendance_request"
                ) or 0

                if buffer_days_for_back_dated_attendance_request > 0:
                    max_allowed_date = add_to_date(
                        getdate(),
                        days=-(int(buffer_days_for_back_dated_attendance_request)+1)
                    )
                    if getdate(self.from_date) < getdate(max_allowed_date):
                        attendance_exists = [
                            a for a in attendance_exists if getdate(a['attendance_date']) < getdate(max_allowed_date)
                        ]

                        if attendance_exists:
                            attendance_list_str = "<br>".join(
                                [f"{format_date(a['attendance_date'])} - {a['name']} ({a['status']})" for a in attendance_exists]
                            )
                            frappe.throw(
                                f"Attendance already exists for the following date(s):<br>{attendance_list_str}",
                            )

    def on_submit(self):
        pass

    def on_cancel(self):
        if self.workflow_state:
            self.db_set("workflow_state", "Cancelled")
        return super().on_cancel()


def get_existing_attendance(employee, from_date, to_date):
    """
    Returns a list of Attendance names for the employee between from_date and to_date,
    excluding cancelled records (docstatus != 2)
    """
    # if from_date == to_date:

    attendance_list = frappe.get_all(
        "Attendance",
        filters={
            "employee": employee,
            "attendance_date": ["between", [from_date, to_date]],
            "docstatus": ["!=", 2]
        },
        fields=["name", "attendance_date", "status"],
        order_by = "attendance_date asc"
    )

    return attendance_list
