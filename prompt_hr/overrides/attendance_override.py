import frappe
from hrms.hr.doctype.attendance.attendance import Attendance, validate_active_employee



class CustomAttendance(Attendance):
    def validate(self):
        from erpnext.controllers.status_updater import validate_status

        validate_status(self.status, ["Present", "Absent", "On Leave", "Half Day", "Work From Home", "WeekOff", "Mispunch"])
        validate_active_employee(self.employee)
        self.validate_attendance_date()
        self.validate_duplicate_record()
        self.validate_overlapping_shift_attendance()
        self.validate_employee_status()
        self.check_leave_record()

    def on_submit(self):
        if self.status == "Half Day" and self.leave_application:
            leave_application = frappe.get_doc("Leave Application", self.leave_application)
            if leave_application.custom_half_day_time:
                self.db_set("custom_half_day_time", leave_application.custom_half_day_time)

    def before_update_after_submit(doc, method=None):
        # ! ONLY HR MANAGER CAN MODIFY STATUS AFTER DOCUMENT IS SUBMITTED
        if doc.docstatus == 1:
            user = frappe.session.user
            # ? CHECK IF THE USER HAS HR ROLES
            has_hr_manager_role = frappe.db.exists({
                "doctype": "Has Role",
                "parent": user,
                "role": ["in", ["S - HR Director (Global Admin)"]]
            })
            if not has_hr_manager_role:
                previous_status = frappe.db.get_value(doc.doctype, doc.name, "status")
                if previous_status != doc.status:
                    frappe.throw(
                        "Only HR Manager can modify the status of the attendance."
                    )