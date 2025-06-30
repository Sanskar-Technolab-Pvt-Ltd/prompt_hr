import frappe

from frappe import throw
from prompt_hr.py.utils import (
    send_notification_email,
    check_user_is_reporting_manager,
    fetch_company_name,
)


def is_valid_for_partial_day(doc, event):
    prompt_company_name = fetch_company_name(prompt=1)

    if not prompt_company_name.get("error") and doc.company == prompt_company_name.get(
        "company_id"
    ):

        partial_day_allowed_minutes = frappe.db.get_single_value(
            "HR Settings", "custom_partial_day_minutes_for_prompt"
        )

        if partial_day_allowed_minutes and doc.custom_partial_day_request_minutes:
            if partial_day_allowed_minutes < doc.custom_partial_day_request_minutes:
                throw(
                    "Allowed Partial Day Minutes are {0}".format(
                        partial_day_allowed_minutes
                    )
                )

    elif prompt_company_name.get("error"):
        throw(prompt_company_name.get("message"))


def before_submit(doc, event):
    if not doc.custom_status:
        throw("Cannot Submit, Status not set")


def validate(doc, event):
    print("fsdbsfdbsfdhbjh")
    try:
        old_status = frappe.db.get_value(
            "Attendance Request", doc.name, "custom_status"
        )

        print(f"Old Status: {old_status}, New Status: {doc.custom_status}\n\n\n")

        # Send additional notification only if status has changed
        if doc.custom_status != old_status and doc.custom_status in [
            "Approved",
            "Rejected",
        ]:
            employee_mail = frappe.db.get_value(
                "Employee", doc.employee, "prefered_email"
            )
            if employee_mail:
                print(f"Sending notification to {employee_mail} for status change")
                send_notification_email(
                    recipients=[employee_mail],
                    notification_name="Attendance Request Status Changed",
                    doctype="Attendance Request",
                    docname=doc.name,
                    fallback_subject="Attendance Request Status Changed",
                    fallback_message=f"<p>Dear User,<br> The status of an attendance request has been changed from <b>{old_status}</b> to <b>{doc.custom_status}</b>. Please take note.</p>",
                )
            else:
                frappe.throw(
                    f"Employee {doc.employee} does not have a preferred email set."
                )
    except Exception as e:
        frappe.log_error(
            f"Error while validating Attendance Request status change: {str(e)}",
            frappe.get_traceback(),
        )
        frappe.throw(str(e))


# * NOTIFYING EMPLOYEE'S REPORTING MANAGER WHEN A ATTENDANCE REQUEST IS CREATED
def notify_reporting_manager(doc, event):
    """Method to send email to employee's reporting manager when employee creates attendance request"""
    try:

        if doc.employee and not doc.custom_status:
            rh_emp = frappe.db.get_value("Employee", doc.employee, "reports_to")
            if not rh_emp:
                throw(f"No Reporting Head found for employee {doc.employee}")

            rh_user_id = frappe.db.get_value("Employee", rh_emp, "user_id")
            if not rh_user_id:
                throw(f"Reporting Head User ID not found from {rh_emp}")

            if event == "after_insert":
                send_notification_email(
                    recipients=[rh_user_id],
                    notification_name="Attendance Request Creation",
                    doctype="Attendance Request",
                    docname=doc.name,
                    fallback_subject=f"Attendance Request Created",
                    fallback_message=f"<p>Dear Reporting Head,<br> An attendance request has been created—please review it at your convenience.</p>",
                )
            if event == "validate" and not doc.is_new():

                # Send generic update notification
                send_notification_email(
                    recipients=[rh_user_id],
                    notification_name="Attendance Request Updated",
                    doctype="Attendance Request",
                    docname=doc.name,
                    fallback_subject=f"Attendance Request Updated",
                    fallback_message=f"<p>Dear Reporting Head,<br> An attendance request has been updated—please review it at your convenience.</p>",
                )

    except Exception as e:
        frappe.log_error(
            f"Error while sending notification to reporting manager",
            frappe.get_traceback(),
        )
        frappe.throw(str(e))
