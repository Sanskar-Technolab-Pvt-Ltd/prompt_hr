import frappe
from frappe import _
from frappe.utils import getdate, date_diff, add_days, format_date, add_to_date, today
from hrms.hr.doctype.attendance_request.attendance_request import AttendanceRequest
from prompt_hr.py.auto_mark_attendance import mark_attendance
from prompt_hr.py.attendance_penalty_api import (
    process_mispunch_penalties_for_prompt,
    process_no_attendance_penalties_for_prompt,
    create_penalty_records,
    process_daily_hours_penalties_for_prompt,
    process_late_entry_penalties_for_prompt,
)
from prompt_hr.py.attendance_penalty_api import check_employee_penalty_criteria
from hrms.hr.utils import validate_active_employee, validate_dates
from frappe.model.workflow import apply_workflow
from prompt_hr.scheduler_methods import send_penalty_warnings

class CustomAttendanceRequest(AttendanceRequest):
    def before_insert(self):
        # ? MAKE CUSTOM STATUS PENDING AS WHILE AMENDING IS REMAIN THE PREVIOUS STATUS
        self.custom_status = "Pending"

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

@frappe.whitelist()
def handle_custom_workflow_action(doc, action, reason_for_rejection=None):
    try:
        if isinstance(doc, str):
            doc = frappe.parse_json(doc)
        if action == "Approve":
            #! ENQUEUE BACKGROUND JOB
            frappe.enqueue(
                process_attendance_and_penalties,
                doc=doc,
                now=False,
            )

            #! GIVE USER MESSAGE
            frappe.msgprint(
                "Your request has been approved and is being processed in the background. "
                "It may take a few minutes to update attendance and penalties. "
                "If it is still not approved after some time, please contact the HR Department."
            )
        elif action == "Reject":
            frappe.enqueue(
                process_rejection_penalties,
                doc=doc,
                now=False,
            )
            if doc.get("doctype") == "Attendance Request" and doc.get("name") and reason_for_rejection:
                frappe.db.set_value("Attendance Request", doc.get("name"),"custom_reason_for_rejection", reason_for_rejection)
                
            frappe.msgprint(
                "Your request has been rejected. No-attendance penalties are being processed "
                "in the background."
            )
        else:
            apply_workflow(doc, action)
    except Exception as e:
        frappe.log_error(
            f"Error in handle_custom_workflow_action",str(e)
        )


def process_attendance_and_penalties(doc):
    from_date = getdate(doc["from_date"])
    to_date = min(getdate(doc["to_date"]), getdate(add_to_date(today(), days=-1, as_string=True)))
    frappe.db.set_value("Attendance Request", doc.get("name"), "custom_status", "Approved")
    process_attendance_request(from_date, to_date, doc, approved_attendance_request=doc.get("name"))
    apply_workflow(doc, "Approve")

def process_rejection_penalties(doc):
    from_date = getdate(doc.get("from_date"))
    to_date = min(getdate(doc.get("to_date")), getdate(add_to_date(today(), days=-1, as_string=True)))
    frappe.db.set_value("Attendance Request", doc.get("name"), "custom_status", "Rejected")
    no_attendance_penalty_enable = frappe.db.get_single_value("HR Settings", "custom_enable_no_attendance_penalty")
    no_attendance_buffer_days = int(frappe.db.get_single_value("HR Settings", "custom_buffer_period_for_no_attendance_penalty_for_prompt")) or 0
    no_attendance_target_date = getdate(add_to_date(today(), days=-(int(no_attendance_buffer_days) + 1)))

    if doc.get("reason") == "Partial Day":
        process_attendance_request(from_date, to_date, doc)
    else:
        if no_attendance_penalty_enable:
            dates = [
                add_days(from_date, i)
                for i in range(date_diff(to_date, from_date) + 1)
            ]
            for date in dates:
                if date <= no_attendance_target_date:
                    penalty_entries = process_no_attendance_penalties_for_prompt(
                        [doc["employee"]],
                        0,
                        date,
                        "custom_no_attendance_leave_penalty_configuration",
                        True,
                    )
                    if penalty_entries:
                        create_penalty_records(penalty_entries, date)
                else:
                    no_attendance_email_records = process_no_attendance_penalties_for_prompt(
                    [doc.employee], no_attendance_buffer_days, date,
                    "custom_no_attendance_leave_penalty_configuration", False
                )   
                    if no_attendance_email_records:
                        email_records_map = {
                            "No Attendance": no_attendance_email_records,
                        }
                        #! MAP BUFFER DAYS FOR EMAIL RECORDS
                        buffer_days_map = {
                            "No Attendance": no_attendance_buffer_days,
                        }

                        consolidated_email_records = {}

                        #! CONSOLIDATE EMAIL WARNINGS
                        for penalty_type, records in email_records_map.items():
                            if not records:
                                continue

                            buffer_days = buffer_days_map[penalty_type]

                            for emp_id, emp_penalties in records.items():
                                if not check_employee_penalty_criteria(emp_id, emp_penalties.get("reason")):
                                    continue

                                att_date = emp_penalties.get("attendance_date")
                                if not att_date:
                                    continue

                                email_date_with_buffer = add_days(att_date, int(buffer_days) + 1)

                                if emp_id not in consolidated_email_records:
                                    consolidated_email_records[emp_id] = {}

                                consolidated_email_records[emp_id][penalty_type] = {
                                    "penalty_date": email_date_with_buffer,
                                    "attendance": emp_penalties.get("attendance"),
                                }

                        #! SEND CONSOLIDATED WARNINGS
                        for emp_id, penalties in consolidated_email_records.items():
                            send_penalty_warnings(emp_id, penalties, date)
    
    apply_workflow(doc, "Reject")


def process_attendance_request(from_date, to_date, doc, approved_attendance_request=None):
    """
    PROCESS ATTENDANCE REQUEST WITH PENALTY AND WARNING LOGIC

    ARGS:
        FROM_DATE (DATE): START DATE OF ATTENDANCE PROCESSING
        TO_DATE (DATE): END DATE OF ATTENDANCE PROCESSING
        DOC (DOCUMENT): EMPLOYEE DOCUMENT REFERENCE
        APPROVED_ATTENDANCE_REQUEST (STR, OPTIONAL): LINKED APPROVED REQUEST
    """

    #! FETCH HR SETTINGS
    hr_settings = frappe.get_single("HR Settings")

    #? PENALTY ENABLE FLAGS
    late_coming_penalty_enable = hr_settings.custom_enable_late_coming_penalty or 0
    daily_hours_penalty_enable = hr_settings.custom_enable_daily_hours_penalty or 0
    mispunch_penalty_enable = hr_settings.custom_enable_mispunch_penalty or 0
    no_attendance_penalty_enable = hr_settings.custom_enable_no_attendance_penalty or 0

    #? CRITERIA & CONFIG VALUES
    percentage_for_daily_hour_penalty = hr_settings.custom_daily_hours_criteria_for_penalty_for_prompt or 0
    late_coming_allowed_per_month = hr_settings.custom_late_coming_allowed_per_month_for_prompt or 0

    #? BUFFER DAYS
    late_coming_buffer_days = hr_settings.custom_buffer_period_for_leave_penalty_for_prompt or 0
    daily_hours_buffer_days = hr_settings.custom_buffer_period_for_daily_hours_penalty_for_prompt or 0
    no_attendance_buffer_days = hr_settings.custom_buffer_period_for_no_attendance_penalty_for_prompt or 0
    mispunch_buffer_days = hr_settings.custom_buffer_days_for_mispunch_penalty or 0

    #? TARGET DATES
    late_coming_target_date = getdate(add_to_date(today(), days=-(int(late_coming_buffer_days) + 1)))
    daily_hours_target_date = getdate(add_to_date(today(), days=-(int(daily_hours_buffer_days) + 1)))
    no_attendance_target_date = getdate(add_to_date(today(), days=-(int(no_attendance_buffer_days) + 1)))
    mispunch_target_date = getdate(add_to_date(today(), days=-(int(mispunch_buffer_days) + 1)))

    #! DATE RANGE
    dates = [add_days(from_date, i) for i in range(date_diff(to_date, from_date) + 1)]

    for date in dates:
        #? MARK ATTENDANCE
        mark_attendance(
            attendance_date=date,
            company=doc.company,
            is_scheduler=0,
            regularize_attendance=0,
            attendance_id=None,
            regularize_start_time=None,
            regularize_end_time=None,
            emp_id=doc.employee,
            approved_attendance_request=approved_attendance_request
        )

        #! INITIALIZE PENALTY RECORDS
        penalties = {
            "Late Coming": {},
            "Daily Hours": {},
            "No Attendance": {},
            "Mispunch": {}
        }
        email_records_map = {
            "Late Coming": {},
            "Daily Hours": {},
            "No Attendance": {},
            "Mispunch": {}
        }

        #? NO ATTENDANCE PENALTY
        if no_attendance_penalty_enable:
            if date <= no_attendance_target_date:
                penalties["No Attendance"] = process_no_attendance_penalties_for_prompt(
                    [doc.employee], 0, date,
                    "custom_no_attendance_leave_penalty_configuration", True
                )
                if penalties["No Attendance"]:
                    create_penalty_records(penalties["No Attendance"], date)
            else:
                email_records_map["No Attendance"] = process_no_attendance_penalties_for_prompt(
                    [doc.employee], no_attendance_buffer_days, date,
                    "custom_no_attendance_leave_penalty_configuration", False
                )

        #? MISPUNCH PENALTY
        if mispunch_penalty_enable:
            if date <= mispunch_target_date:
                penalties["Mispunch"] = process_mispunch_penalties_for_prompt(
                    [doc.employee], 0, date,
                    "custom_attendance_mispunch_leave_penalty_configuration", True
                )
                if penalties["Mispunch"]:
                    create_penalty_records(penalties["Mispunch"], date)
            else:
                email_records_map["Mispunch"] = process_mispunch_penalties_for_prompt(
                    [doc.employee], mispunch_buffer_days, date,
                    "custom_attendance_mispunch_leave_penalty_configuration", False
                )

        #? DAILY HOURS PENALTY
        if daily_hours_penalty_enable:
            if date <= daily_hours_target_date:
                penalties["Daily Hours"] = process_daily_hours_penalties_for_prompt(
                    [doc.employee], 0, date,
                    percentage_for_daily_hour_penalty,
                    "custom_daily_hour_leave_penalty_configuration", True
                )
                if penalties["Daily Hours"]:
                    create_penalty_records(penalties["Daily Hours"], date)
            else:
                email_records_map["Daily Hours"] = process_daily_hours_penalties_for_prompt(
                    [doc.employee], daily_hours_buffer_days, date,
                    percentage_for_daily_hour_penalty,
                    "custom_daily_hour_leave_penalty_configuration", False
                )

        #? LATE COMING PENALTY
        if late_coming_penalty_enable:
            if date <= late_coming_target_date:
                penalties["Late Coming"] = process_late_entry_penalties_for_prompt(
                    [doc.employee], late_coming_allowed_per_month, 0,
                    "custom_late_coming_leave_penalty_configuration", date, True
                )
                if penalties["Late Coming"]:
                    create_penalty_records(penalties["Late Coming"], date)
            else:
                email_records_map["Late Coming"] = process_late_entry_penalties_for_prompt(
                    [doc.employee], late_coming_allowed_per_month, late_coming_buffer_days,
                    "custom_late_coming_leave_penalty_configuration", date, False
                )

        #! MAP BUFFER DAYS FOR EMAIL RECORDS
        buffer_days_map = {
            "Late Coming": late_coming_buffer_days,
            "Daily Hours": daily_hours_buffer_days,
            "No Attendance": no_attendance_buffer_days,
            "Mispunch": mispunch_buffer_days,
        }

        consolidated_email_records = {}

        #! CONSOLIDATE EMAIL WARNINGS
        for penalty_type, records in email_records_map.items():
            if not records:
                continue

            buffer_days = buffer_days_map[penalty_type]

            for emp_id, emp_penalties in records.items():
                if not check_employee_penalty_criteria(emp_id, emp_penalties.get("reason")):
                    continue

                att_date = emp_penalties.get("attendance_date")
                if not att_date:
                    continue

                email_date_with_buffer = add_days(att_date, int(buffer_days) + 1)

                if emp_id not in consolidated_email_records:
                    consolidated_email_records[emp_id] = {}

                consolidated_email_records[emp_id][penalty_type] = {
                    "penalty_date": email_date_with_buffer,
                    "attendance": emp_penalties.get("attendance"),
                }

        #! SEND CONSOLIDATED WARNINGS
        for emp_id, penalties in consolidated_email_records.items():
            send_penalty_warnings(emp_id, penalties, date)


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
