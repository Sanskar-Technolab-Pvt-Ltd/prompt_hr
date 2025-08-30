import frappe
from frappe import _
from frappe.utils import getdate, date_diff, add_days
from hrms.hr.doctype.attendance_request.attendance_request import AttendanceRequest
from prompt_hr.py.auto_mark_attendance import mark_attendance
from prompt_hr.py.attendance_penalty_api import (
    process_mispunch_penalties_for_prompt,
    process_no_attendance_penalties_for_prompt,
    create_penalty_records,
    process_daily_hours_penalties_for_prompt,
    process_late_entry_penalties_for_prompt,
)
from frappe.model.workflow import apply_workflow

class CustomAttendanceRequest(AttendanceRequest):

    def before_submit(self):
        if self.workflow_state == "Approved":
            self.custom_status = "Approved"



        elif self.workflow_state == "Rejected":
            self.custom_status = "Rejected"

    def on_submit(self):
        pass

    def on_cancel(self):
        if self.workflow_state:
            self.db_set("workflow_state", "Cancelled")
        return super().on_cancel()

@frappe.whitelist()
def handle_custom_workflow_action(doc, action):
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

        frappe.msgprint(
            "Your request has been rejected. No-attendance penalties are being processed "
            "in the background."
        )
    else:
        apply_workflow(doc, action)


def process_attendance_and_penalties(doc):
    from_date = getdate(doc["from_date"])
    to_date = min(getdate(doc["to_date"]), getdate())

    penalty_settings = frappe.db.get_value(
        "HR Settings",
        None,
        [
            "custom_enable_late_coming_penalty",
            "custom_enable_daily_hours_penalty",
            "custom_enable_mispunch_penalty",
            "custom_enable_no_attendance_penalty",
            "custom_daily_hours_criteria_for_penalty_for_prompt",
            "custom_late_coming_allowed_per_month_for_prompt",
        ],
        as_dict=True,
    )

    #! ACCESS VALUES
    late_coming_penalty_enable = penalty_settings.custom_enable_late_coming_penalty
    daily_hours_penalty_enable = penalty_settings.custom_enable_daily_hours_penalty
    mispunch_penalty_enable = penalty_settings.custom_enable_mispunch_penalty
    no_attendance_penalty_enable = penalty_settings.custom_enable_no_attendance_penalty
    percentage_for_daily_hour_penalty = penalty_settings.custom_daily_hours_criteria_for_penalty_for_prompt
    late_coming_allowed_per_month = int(penalty_settings.custom_late_coming_allowed_per_month_for_prompt)

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
    
    apply_workflow(doc, "Approve")

def process_rejection_penalties(doc):
    from_date = getdate(doc.get("from_date"))
    to_date = min(getdate(doc.get("to_date")), getdate("2025-10-05"))

    penalty_settings = frappe.db.get_value(
        "HR Settings",
        None,
        ["custom_enable_no_attendance_penalty"],
        as_dict=True,
    )

    if penalty_settings.custom_enable_no_attendance_penalty:
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
