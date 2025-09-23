import frappe
from hrms.hr.doctype.attendance.attendance import Attendance, validate_active_employee
from frappe.utils import get_link_to_form, format_date, getdate, add_to_date, today, get_datetime
from prompt_hr.py.attendance_penalty_api import create_penalty_records, process_no_attendance_penalties_for_prompt, process_daily_hours_penalties_for_prompt, process_late_entry_penalties_for_prompt, process_mispunch_penalties_for_prompt
from prompt_hr.prompt_hr.doctype.employee_penalty.employee_penalty import cancel_penalties

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


def modify_employee_penalty(employee, attendance_date):
    hr_settings = frappe.get_single("HR Settings")
    today_date = getdate()
    attendance_date = getdate(attendance_date)
    penalty_buffer_days = hr_settings.custom_buffer_days_for_penalty or 0
    penalty_date = getdate(
        add_to_date(attendance_date, days=(int(penalty_buffer_days)+1))
    )
    if today_date >= penalty_date:
        if today_date == penalty_date:
            time = get_datetime().time()
            if time.hour <= 3:
                return
            
        try:
            employee_penalty = frappe.get_all(
                "Employee Penalty",
                {
                    "employee": employee,
                    "penalty_date": attendance_date,
                    "is_leave_balance_restore": 0,
                },
            )
            if employee_penalty:
                for penalty in employee_penalty:
                    cancel_penalties(penalty.name, reason="Attendance Modified", attendance_modified=1)
                    frappe.delete_doc("Employee Penalty", penalty.name)
        except:
            frappe.log_error(
                "Error in Canceling Penalties", str(e)
            )
        # ! FETCH ENABLE PENALTY
        try:
            late_coming_penalty_enable = hr_settings.custom_enable_late_coming_penalty or 0
        except Exception as e:
            late_coming_penalty_enable = 0
            frappe.log_error(
                "Enable Late Coming Penalty", str(e)
            )
        
        try:
            daily_hour_penalty_enable = hr_settings.custom_enable_daily_hours_penalty
        except Exception as e:
            daily_hour_penalty_enable = 0
            frappe.log_error(
                "Enable Daily Hours Penalty", str(e)
            )

        try:
            no_attendance_penalty_enable = hr_settings.custom_enable_no_attendance_penalty
        except Exception as e:
            no_attendance_penalty_enable = 0
            frappe.log_error(
                "Enable No Attendance Penalty", str(e)
            )
        
        try:
            mispunch_penalty_enable = hr_settings.custom_enable_mispunch_penalty
        except Exception as e:
            mispunch_penalty_enable = 0
            frappe.log_error(
                "Enable Mispunch Penalty", str(e)
            )
        # ? LATE COMING PENALTY CONFIGURATION
        try:
            late_coming_allowed_per_month = (
                hr_settings.custom_late_coming_allowed_per_month_for_prompt or 0
            )
        except Exception as e:
            late_coming_allowed_per_month = 0
            frappe.log_error(
                "Late Coming Allowed For Month", str(e)
            )

        # ? DAILY HOURS PERCENTAGE FOR PENALTY
        try:
            percentage_for_daily_hour_penalty = (
                hr_settings.custom_daily_hours_criteria_for_penalty_for_prompt
            )
        except Exception as e:
            percentage_for_daily_hour_penalty = 42
            frappe.log_error(
                "Percentage For Daily Hours Penalty", str(e)
            )
        if late_coming_penalty_enable:
            late_penalty = process_late_entry_penalties_for_prompt(
            [employee],
            late_coming_allowed_per_month,
            0,
            "custom_late_coming_leave_penalty_configuration",
            attendance_date,
            True
        )
            if late_penalty:
                create_penalty_records(late_penalty, attendance_date)

        if daily_hour_penalty_enable:
            daily_hour_penalty = process_daily_hours_penalties_for_prompt(
            [employee],
            0,
            attendance_date,
            percentage_for_daily_hour_penalty,
            "custom_daily_hour_leave_penalty_configuration",
            True
        )
            if daily_hour_penalty:
                create_penalty_records(daily_hour_penalty, attendance_date)

        if mispunch_penalty_enable:
            mispunch_penalty = process_mispunch_penalties_for_prompt(
                [employee],
                0,
                attendance_date,
                "custom_attendance_mispunch_leave_penalty_configuration",
                True
            )
            if mispunch_penalty:
                create_penalty_records(mispunch_penalty, attendance_date)

        if no_attendance_penalty_enable:
            no_attendance_penalty = process_no_attendance_penalties_for_prompt(
                [employee],
                0,
                attendance_date,
                "custom_no_attendance_leave_penalty_configuration",
                True,
            )
            if no_attendance_penalty:
                create_penalty_records(no_attendance_penalty,attendance_date)
