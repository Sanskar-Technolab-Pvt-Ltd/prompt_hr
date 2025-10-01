# Copyright (c) 2025, Jignasha Chavda and contributors
# For license information, please see license.txt

import frappe
from frappe import _, throw
from frappe.utils import getdate, today, formatdate
from frappe.model.document import Document
from prompt_hr.py.utils import (
    send_notification_email,
    is_user_reporting_manager_or_hr,
    get_reporting_manager_info,
)
from prompt_hr.overrides.attendance_override import modify_employee_penalty
from prompt_hr.prompt_hr.doctype.employee_penalty.employee_penalty import (
    cancel_penalties,
)
from prompt_hr.py.auto_mark_attendance import mark_attendance


class WeekOffChangeRequest(Document):

    def before_save(self):

        # ? CHECK IF ANY LEAVE APPLICATION EXISTS FOR THE DATES ENTERED IN WEEKOFF CHANGE REQUEST
        check_if_leave_application_exists(self)

    def on_update(self):
        if self.workflow_state == "Pending":
            manager_info = get_reporting_manager_info(self.employee)
            if manager_info:
                self.db_set(
                    "pending_approval_at",
                    f"{manager_info['name']} - {manager_info['employee_name']}",
                )
        else:
            self.db_set("pending_approval_at", "")

    def before_insert(self):

        # * CHECKING IF THE DAY IS ENTERED OR NOT AND IF ENTERED THEN THE DAY IS CORRECT OR NOT ACCORDING TO DATE
        if self.weekoff_details:
            for row in self.weekoff_details:
                if row.existing_weekoff_date:
                    day_name = get_day_name(row.existing_weekoff_date)
                    if not row.existing_weekoff:
                        row.existing_weekoff = day_name
                    elif (
                        row.existing_weekoff
                        and row.existing_weekoff.lower() != day_name.lower()
                    ):
                        throw("Please Set Correct Existing weekoff Day as per the date")

                if row.new_weekoff_date:
                    day_name = get_day_name(row.new_weekoff_date)
                    if not row.new_weekoff:
                        row.new_weekoff = day_name
                    elif (
                        row.new_weekoff and row.new_weekoff.lower() != day_name.lower()
                    ):
                        throw("Please Set Correct New weekoff Day as per the date")

    def validate(self):

        # *CHECKING IF THE EXISTING DETAILS IS VALID OR NOT, IF INVALID SHOWING AN ALERT TELLING USER THAT THE EXISTING DATE ENTERED DOES NOT EXISTS IN HOLIDAY LIST
        if self.weekoff_details:
            for row in self.weekoff_details:
                exists = check_existing_date(self.employee, row.existing_weekoff_date)
                if not exists.get("error"):
                    if not exists.get("exists"):
                        throw(
                            f"Date {row.existing_weekoff_date} does not exist in holiday list"
                        )
                    else:
                        if row.existing_weekoff_date:
                            day_name = get_day_name(row.existing_weekoff_date)
                            if not row.existing_weekoff:
                                row.existing_weekoff = day_name
                            elif (
                                row.existing_weekoff
                                and row.existing_weekoff.lower() != day_name.lower()
                            ):
                                throw(
                                    f"The date {formatdate(row.existing_weekoff_date, 'dd-mm-yyyy')} does not exist in the holiday list for this employee."
                                )

                        if row.new_weekoff_date:
                            day_name = get_day_name(row.new_weekoff_date)
                            if not row.new_weekoff:
                                row.new_weekoff = day_name
                            elif (
                                row.new_weekoff
                                and row.new_weekoff.lower() != day_name.lower()
                            ):
                                throw(
                                    "Please Set Correct New weekoff Day as per the date"
                                )
                elif exists.get("error"):
                    throw(
                        f"Error While Verifying Existing Date {exists.get('message')}"
                    )

        # *CHECKING IF THE CURRENT USER IS THE EMPLOYEE USER LINKED TO DOCUMENT THEN WHEN WE SAVES THIS DOCUMENT THEN SENDING AN EMAIL TO THE EMPLOYEE'S REPORTING HEAD ABOUT THE CREATION WEEKOFF CHANGE REQUEST
        current_user = frappe.session.user
        if self.status == "Approved":
            is_rh = is_user_reporting_manager_or_hr(current_user, self.employee)
            #! PROCESS WEEKOFF CHANGES FOR EMPLOYEE
            if not is_rh.get("error"):
                today = getdate()

                def process_weekoff_attendance(date, is_existing):
                    att_list = frappe.get_all(
                        "Attendance",
                        filters={
                            "employee": self.employee,
                            "docstatus": ["!=", 2],
                            "attendance_date": date,
                        },
                        fields=[
                            "name",
                            "attendance_date",
                            "custom_employee_penalty_id",
                        ],
                        limit=1,
                    )

                    if att_list:
                        attendance = att_list[0]

                        # Cancel penalties if any
                        if attendance.custom_employee_penalty_id:
                            cancel_penalties(
                                attendance.custom_employee_penalty_id,
                                "Weekoff change request Approve",
                                1,
                            )

                        # Cancel old attendance
                        frappe.get_doc("Attendance", attendance.name).cancel()
                    print("ATtendance")
                    # Mark attendance
                    mark_attendance(
                        attendance_date=date,
                        company=self.company,
                        regularize_attendance=0,
                        emp_id=self.employee,
                    )

                    # Update employee penalty
                    modify_employee_penalty(self.employee, date, is_existing)

                for weekoff_detail in self.weekoff_details:
                    existing_date = getdate(weekoff_detail.existing_weekoff_date)
                    if existing_date < today:
                        process_weekoff_attendance(
                            weekoff_detail.existing_weekoff_date, True
                        )

                    new_date = getdate(weekoff_detail.new_weekoff_date)
                    if new_date < today:
                        process_weekoff_attendance(
                            weekoff_detail.new_weekoff_date, False
                        )

            if not is_rh.get("error") and is_rh.get("is_rh"):
                emp_user_id = frappe.db.get_value("Employee", self.employee, "user_id")
                if emp_user_id:
                    # if "@" in emp_user_id:
                    # 	emp_mail = emp_user_id
                    # else:
                    # emp_mail = frappe.db.get_value("User", emp_user_id, 'email')
                    send_notification_email(
                        recipients=[emp_user_id],
                        notification_name="WeekOff Change Request Approved",
                        doctype="WeekOff Change Request",
                        docname=self.name,
                        send_link=True,
                        fallback_subject="WeekOff Change Request Approved",
                        fallback_message=f"<p>Dear Employee</p>   <p>Your WeekOff Change Request has been reviewed and approved.<br>Best regards,<br>HR Department</p>",
                    )
            elif is_rh.get("error"):
                throw(f"{is_rh.get('message')}")
        if self.status == "Rejected":
            is_rh = is_user_reporting_manager_or_hr(current_user, self.employee)
            if not is_rh.get("error") and is_rh.get("is_rh"):
                emp_user_id = frappe.db.get_value("Employee", self.employee, "user_id")
                if emp_user_id:
                    send_notification_email(
                        recipients=[emp_user_id],
                        notification_name="WeekOff Change Request Rejected",
                        doctype="WeekOff Change Request",
                        docname=self.name,
                        send_link=True,
                        fallback_subject="WeekOff Change Request Rejected",
                        fallback_message=f"<p>Dear Employee</p>\n\n    <p>We regret to inform you that your WeekOff Change Request has been rejected.</p>",
                    )
            elif is_rh.get("error"):
                throw(f"{is_rh.get('message')}")

        if self.workflow_state == "Approved":

            # ? CREATE AND LINK NEW HOLIDAY LIST IF NOT EXISTS
            holiday_list = frappe.db.get_value(
                "Employee", self.employee, "holiday_list"
            )
            if not holiday_list:
                frappe.throw(
                    _("Please set Holiday List for Employee {0}").format(self.employee)
                )

            weekoff_details = self.weekoff_details

            # ? CREATE NEW HOLIDAY LIST IF NOT EXISTS
            create_new_holiday_list(holiday_list, weekoff_details)

    def after_insert(self):

        current_user = frappe.session.user
        emp_user = frappe.db.get_value("Employee", self.employee, "user_id")

        # * NOTIFY REPORTING MANAGER IF THE CURRENT USER IS THE EMPLOYEE WHOSE WEEKOFF CHANGE REQUEST IS RAISED FOR
        notify_reporting_manager(self.employee, self.name, emp_user, current_user)

    def before_validate(self):
        if not self.is_new():
            if self.workflow_state == "Rejected":
                self.status = "Rejected"
            elif self.workflow_state == "Approved":
                self.status = "Approved"


def notify_reporting_manager(employee_id, docname, emp_user, current_user):
    """Method to check if the current user is the employee whose weekoff change request is, if it is the same user then, sending an email to  employee's reporting manager"""
    rh_emp = frappe.db.get_value("Employee", employee_id, "reports_to")
    if rh_emp:
        rh_user = frappe.db.get_value("Employee", rh_emp, "user_id")
        if rh_user:
            if current_user == emp_user:
                send_notification_email(
                    recipients=[rh_user],
                    notification_name="Request to RH to Approve WeekOff Change",
                    doctype="WeekOff Change Request",
                    docname=docname,
                    send_link=True,
                    fallback_subject=" Request for Approval – WeekOff Change Request",
                    fallback_message=f"Dear Reporting Head,\n\n     I am writing to formally request your approval for my WeekOff Change Request.\n Kindly review and approve the request at your earliest convenience.",
                )
        else:
            throw(f"No user found for reporting head {rh_emp}")
    else:
        throw(f"NO Reporting Head Found for Employee {employee_id}")


@frappe.whitelist()
def check_existing_date(employee_id, existing_date):
    """Method to check of the existing date entered exists in holiday list's holiday child table or not"""
    try:
        holiday_list_id = (
            frappe.db.get_value("Employee", employee_id, "holiday_list") or None
        )

        if holiday_list_id:
            is_existing = frappe.db.get_all(
                "Holiday",
                {
                    "parenttype": "Holiday List",
                    "parent": holiday_list_id,
                    "holiday_date": existing_date,
                },
                "name",
                limit=1,
            )

            if is_existing:
                return {"error": 0, "exists": 1}
            else:
                return {"error": 0, "exists": 0}
        else:
            return {"error": 1, "message": f"No Holiday List found for {employee_id}"}
    except Exception as e:
        frappe.log_error("Error While Verifying Existing Date", frappe.get_traceback())
        return {"error": 1, "message": f"{str(e)}"}


def get_day_name(date_value):
    try:
        date_value = getdate(date_value)
        day_name = date_value.strftime("%A")
        return day_name
    except Exception as e:
        throw("Error while Getting Date Day name")


# ? FUNCTION TO CHECK IF ANY LEAVE APPLICATION EXISTS FOR THE DATES ENTERED IN WEEKOFF CHANGE REQUEST
def check_if_leave_application_exists(doc):
    weekoff_details = doc.weekoff_details

    # ? ALLOW REJECTION WITHOUT BLOCKING
    if doc.workflow_state == "Rejected":
        print("Rejected State - No Check Needed")
        return

    if weekoff_details:
        for row in weekoff_details:
            if row.existing_weekoff_date:
                leave_app = frappe.db.get_all(
                    "Leave Application",
                    {
                        "employee": doc.employee,
                        "from_date": row.existing_weekoff_date,
                        "to_date": row.existing_weekoff_date,
                        "docstatus": ["!=", 2],
                    },
                    ["name"],
                    limit=1,
                )
                if leave_app:
                    link = f"/app/leave-application/{leave_app[0].name}"
                    frappe.throw(
                        msg=f"""Leave Application <a href="{link}" style="font-weight: bold;">
                                {leave_app[0].name}</a> exists for Existing WeekOff Date {formatdate(row.existing_weekoff_date, 'dd-mm-yyyy')}""",
                        title="Leave Application Exists",
                    )

            if row.new_weekoff_date:
                leave_app = frappe.db.get_all(
                    "Leave Application",
                    {
                        "employee": doc.employee,
                        "from_date": row.new_weekoff_date,
                        "to_date": row.new_weekoff_date,
                        "status": ["!=", "Cancelled"],
                    },
                    ["name"],
                    limit=1,
                )
                if leave_app:
                    link = f"/app/leave-application/{leave_app[0].name}"
                    frappe.throw(
                        msg=f"""Leave Application <a href="{link}" style="font-weight: bold;">
                                {leave_app[0].name}</a> exists for New WeekOff Date {formatdate(row.new_weekoff_date, 'dd-mm-yyyy')}""",
                        title="Leave Application Exists",
                    )


# ? FUNCTION TO UPDATE HOLIDAY LIST WITH NEW WEEK-OFF DATES
def create_new_holiday_list(holiday_list, weekoff_details):
    """
    Replace week-off dates in the Holiday List with new ones.
    Other existing holidays remain unchanged.
    """

    if not weekoff_details:
        return

    # ? FETCH HOLIDAY LIST DOC
    holiday_list_doc = frappe.get_doc("Holiday List", holiday_list)

    # ? REMOVE EXISTING WEEK-OFF HOLIDAYS (optional: identify by description containing 'WeekOff Changed')
    holiday_list_doc.holiday_details = [
        row for row in holiday_list_doc.holiday_details
        if "WeekOff Changed" not in row.description
    ]

    # ? ADD NEW WEEK-OFF DATES
    for row in weekoff_details:
        old_date = row.get("old_weekoff_date")
        new_date = row.get("new_weekoff_date")
        if old_date and new_date:
            holiday_list_doc.append(
                "holiday_details",
                {
                    "holiday_date": new_date,
                    "description": f"WeekOff Changed from {frappe.utils.formatdate(old_date, 'dd-mm-yyyy')} "
                                   f"to {frappe.utils.formatdate(new_date, 'dd-mm-yyyy')}",
                },
            )

    # ? SAVE AND COMMIT
    holiday_list_doc.save()
    frappe.db.commit()
