import frappe
from frappe import _
from frappe.utils import getdate, date_diff, add_days, format_date
from hrms.hr.doctype.attendance_request.attendance_request import AttendanceRequest
from prompt_hr.py.auto_mark_attendance import mark_attendance
from prompt_hr.py.attendance_penalty_api import (
    process_mispunch_penalties_for_prompt,
    process_no_attendance_penalties_for_prompt,
    create_penalty_records,
    process_daily_hours_penalties_for_prompt,
    process_late_entry_penalties_for_prompt,
)
from hrms.hr.utils import validate_active_employee, validate_dates
from frappe.model.workflow import apply_workflow

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
    to_date = min(getdate(doc["to_date"]), getdate())
    frappe.db.set_value("Attendance Request", doc.get("name"), "custom_status", "Approved")
    process_attendance_request(from_date, to_date, doc, approved_attendance_request=doc.get("name"))
    apply_workflow(doc, "Approve")

def process_rejection_penalties(doc):
    from_date = getdate(doc.get("from_date"))
    to_date = min(getdate(doc.get("to_date")), getdate())
    frappe.db.set_value("Attendance Request", doc.get("name"), "custom_status", "Rejected")
    no_attendance_penalty_enable = frappe.db.get_single_value("HR Settings", "custom_enable_no_attendance_penalty")

    if doc.get("reason") == "Partial Day":
        process_attendance_request(from_date, to_date, doc)
    else:
        if no_attendance_penalty_enable:
            dates = [
                add_days(from_date, i)
                for i in range(date_diff(to_date, from_date) + 1)
            ]
            for date in dates:
                penalty_entries = process_no_attendance_penalties_for_prompt(
                    [doc["employee"]],
                    0,
                    date,
                    "custom_no_attendance_leave_penalty_configuration",
                    True,
                )
                if penalty_entries:
                    create_penalty_records(penalty_entries, date)
    
    apply_workflow(doc, "Reject")


def process_attendance_request(from_date, to_date, doc, approved_attendance_request=None):
    late_coming_penalty_enable = frappe.db.get_single_value("HR Settings", "custom_enable_late_coming_penalty")
    daily_hours_penalty_enable = frappe.db.get_single_value("HR Settings", "custom_enable_daily_hours_penalty")
    mispunch_penalty_enable = frappe.db.get_single_value("HR Settings", "custom_enable_mispunch_penalty")
    no_attendance_penalty_enable = frappe.db.get_single_value("HR Settings", "custom_enable_no_attendance_penalty")
    percentage_for_daily_hour_penalty = frappe.db.get_single_value("HR Settings", "custom_daily_hours_criteria_for_penalty_for_prompt")
    late_coming_allowed_per_month = int(frappe.db.get_single_value("HR Settings", "custom_late_coming_allowed_per_month_for_prompt"))

    dates = [
        add_days(from_date, i)
        for i in range(date_diff(to_date, from_date) + 1)
    ]

    for date in dates:
        mark_attendance(
            attendance_date=date,
            company=doc.company,
            is_scheduler=0,
            regularize_attendance=0,
            attendance_id=None,
            regularize_start_time=None,
            regularize_end_time=None,
            emp_id=doc.employee,
            approved_attendance_request = approved_attendance_request
        )
        no_attendance_penalty = {}
        mispunch_penalty = {}
        late_penalty = {}
        daily_hour_penalty = {}
        if no_attendance_penalty_enable:
            no_attendance_penalty = process_no_attendance_penalties_for_prompt(
                [doc.employee],
                0,
                date,
                "custom_no_attendance_leave_penalty_configuration",
                True,
            )
            if no_attendance_penalty:
                create_penalty_records(no_attendance_penalty,date)
        if mispunch_penalty_enable:
            mispunch_penalty = process_mispunch_penalties_for_prompt(
                [doc.employee],
                0,
                date,
                "custom_attendance_mispunch_leave_penalty_configuration",
                True
            )
            if mispunch_penalty:
                create_penalty_records(mispunch_penalty, date)
        if daily_hours_penalty_enable:
            daily_hour_penalty = process_daily_hours_penalties_for_prompt(
                [doc.employee],
                0,
                date,
                percentage_for_daily_hour_penalty,
                "custom_daily_hour_leave_penalty_configuration",
                True
            )
            if daily_hour_penalty:
                create_penalty_records(daily_hour_penalty, date)
        if late_coming_penalty_enable:
            late_penalty = process_late_entry_penalties_for_prompt(
                [doc.employee],
                late_coming_allowed_per_month,
                0,
                "custom_late_coming_leave_penalty_configuration",
                date,
                True
            )
            if late_penalty:
                create_penalty_records(late_penalty, date)


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
