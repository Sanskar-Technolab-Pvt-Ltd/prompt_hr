import frappe

from frappe import _
from frappe.utils import get_link_to_form, formatdate
from hrms.hr.doctype.leave_application.leave_application import LeaveApplication, AttendanceAlreadyMarkedError
from hrms.mixins.pwa_notifications import PWANotificationsMixin



class CustomLeaveApplication(LeaveApplication, PWANotificationsMixin):
    def validate_attendance(self):
        if not self.custom_is_penalty_leave:
            attendance_dates = frappe.get_all(
                "Attendance",
                filters={
                    "employee": self.employee,
                    "attendance_date": ("between", [self.from_date, self.to_date]),
                    "status": ("in", ["Present", "Half Day", "Work From Home"]),
                    "docstatus": 1,
                },
                fields=["name", "attendance_date"],
                order_by="attendance_date",
            )
            if attendance_dates:
                frappe.throw(
                    _("Attendance for employee {0} is already marked for the following dates: {1}").format(
                        self.employee,
                        (
                            "<br><ul><li>"
                            + "</li><li>".join(
                                get_link_to_form("Attendance", a.name, label=formatdate(a.attendance_date))
                                for a in attendance_dates
                            )
                            + "</li></ul>"
                        ),
                    ),
                    AttendanceAlreadyMarkedError,
                )