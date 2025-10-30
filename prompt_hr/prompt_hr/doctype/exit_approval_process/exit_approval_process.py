# Copyright (c) 2025, Jignasha Chavda and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document
from frappe import _
from datetime import datetime
from frappe.utils import nowdate, today, add_days, getdate, formatdate
from prompt_hr.py.utils import (
    send_notification_email,
    get_hr_managers_by_company,
    get_prompt_company_name,
    get_indifoss_company_name,
    get_roles_from_hr_settings_by_module,
    get_email_ids_for_roles
)


# ? MAIN EXIT APPROVAL CLASS
class ExitApprovalProcess(Document):

    def before_save(self):
        # ? SET EXIT QUESTIONNAIRE AND EXIT CHECKLIST DATES
        exit_questionnaire_days = frappe.db.get_value("HR Settings", None, "custom_days_before_exit_questionnaire_prompt") or 0
        if self.last_date_of_working:
            exit_questionnaire_date = add_days(self.last_date_of_working, -(int(exit_questionnaire_days)+1))
            self.custom_exit_questionnaire_notification_date  = formatdate(exit_questionnaire_date)

        exit_checklist_days = frappe.db.get_value("HR Settings", None, "custom_days_before_exit_checklist_prompt") or 0
        if self.last_date_of_working:
            exit_checklist_date = add_days(self.last_date_of_working, -(int(exit_checklist_days)+1))
            self.custom_exit_checklist_notification_date = formatdate(exit_checklist_date)
    
        # ? VALIDATE APPROVAL STATUS
        validate_approval_status(self)

    def on_update(self):
        if self.resignation_approval == "Approved":
            # ? UPDATE RELIEVING DATE IF CHANGED
            if (
                frappe.db.get_value("Employee", self.employee, "relieving_date")
                != self.last_date_of_working
            ):
                frappe.db.set_value(
                    "Employee",
                    self.employee,
                    "relieving_date",
                    self.last_date_of_working,
                )

                if getdate(self.last_date_of_working) < getdate(today()):
                    frappe.db.set_value(
                        "Employee",
                        self.employee,
                        "status",
                        "Left",
                    )

                    try:
                        user_id = frappe.db.get_value("Employee", self.employee, "user_id")
                        if user_id:
                            if user_id != "Administrator":
                                frappe.db.set_value("User", user_id, "enabled", 0)

                    except Exception as e:
                        frappe.log_error("Error in Making User Disable", str(e))

        if self.workflow_state == "Approved by Reporting Manager" and self.has_value_changed("workflow_state"):
            try:
                enable_exit_emails = frappe.db.get_single_value("HR Settings", "custom_enable_exit_mails") or 0
                #! DEFINE HR ROLES THAT SHOULD RECEIVE WORKFLOW UPDATES
                
                hr_roles = get_roles_from_hr_settings_by_module("custom_hr_roles_for_exit")

                recipients = set()

                #! ADD EMPLOYEE USER ID AS RECIPIENT (FOR SELF-STATUS AWARENESS)
                employee_user_id = frappe.db.get_value("Employee", self.employee, "user_id")
                if employee_user_id:
                    recipients.add(employee_user_id)

                #! GET ALL USERS WHO HAVE HR ROLES
                all_hr_emails = get_email_ids_for_roles(hr_roles)
                recipients.update(all_hr_emails)
                recipients = list(recipients)

                if recipients:
                    # Send generic update notification
                    if enable_exit_emails:
                        send_notification_email(
                            recipients=recipients,
                            notification_name="Exit Approval Process Update Status",
                            doctype="Exit Approval Process",
                            docname=self.name,
                            send_link=False,
                            fallback_subject=f"Exit Approval Process: {self.workflow_state} - {self.employee}",
                            fallback_message=f"<p>Dear Team,<br> An Exit Approval Process has been {self.workflow_state}.</p>",
                            send_header_greeting = True,
                        )

            except Exception as e:
                frappe.log_error("Sending Mail to HR in Exit Approval Process", str(e))


# ? RAISE EXIT CHECKLIST OR SCHEDULE IT
@frappe.whitelist()
def raise_exit_checklist(employee, company, exit_approval_process):
    doc = frappe.get_doc("Exit Approval Process", exit_approval_process)
    today_date = getdate(today())
    date_str = doc.custom_exit_checklist_notification_date
    notif_date = datetime.strptime(date_str, "%d-%m-%Y").strftime("%Y-%m-%d")

    # ? SKIP IF FUTURE
    if getdate(notif_date) > today_date:
        return {
            "status": "info",
            "message": _("Exit Checklist notification will be sent on {0}").format(
                formatdate(notif_date)
            ),
        }

    return create_employee_separation(employee, company, exit_approval_process)


# ? CREATE EMPLOYEE SEPARATION RECORD
def create_employee_separation(employee, company, exit_approval_process):
    if existing := frappe.db.get_value("Employee Separation", {"employee": employee}):
        frappe.db.set_value(
            "Exit Approval Process",
            exit_approval_process,
            "employee_separation",
            existing,
        )
        return {
            "status": "info",
            "message": _("Employee Separation record already exists."),
        }

    emp = frappe.db.get_value(
        "Employee", employee, ["designation", "department", "grade"], as_dict=True
    )
    template = frappe.get_all(
        "Employee Separation Template",
        {
            "company": company,
            "designation": ["in", [emp.designation, ""]],
            "department": ["in", [emp.department, ""]],
            "employee_grade": ["in", [emp.grade, ""]],
        },
        ["name"],
        limit=1,
    )

    doc = frappe.new_doc("Employee Separation")
    doc.update(
        {"employee": employee, "company": company, "boarding_begins_on": nowdate()}
    )

    if template:
        doc.employee_separation_template = template[0].name
        activities = frappe.get_all(
            "Employee Boarding Activity",
            filters={"parent": template[0].name},
            fields=["*"],
        )
        for act in activities:
            try:
                act.custom_is_raised = 1
            except:
                frappe.log_error("In Setting custom_is_raised field")
            doc.append("activities", act)

        # ? SET EMPLOYEE REPORTING MANAGER AS A USER IN SEPARATION ACTIVITY FIRST RECORD
        reporting_manager = frappe.db.get_value("Employee", employee, "reports_to")
        if reporting_manager:
            reporting_manager_id = frappe.db.get_value("Employee", reporting_manager, "user_id")
            if reporting_manager_id:
                if len(doc.activities) > 0:
                    doc.activities[0].user = reporting_manager_id

    doc.insert(ignore_permissions=True)
    frappe.db.commit()
    frappe.db.set_value(
        "Exit Approval Process", exit_approval_process, "employee_separation", doc.name
    )

    return {
        "status": "success",
        "message": _("Employee Separation created successfully."),
    }


# ? RAISE EXIT INTERVIEW OR SCHEDULE IT
@frappe.whitelist()
def raise_exit_interview(employee, company, exit_approval_process):
    if existing := frappe.db.get_value("Exit Interview", {"employee": employee}):
        frappe.db.set_value(
            "Exit Approval Process",
            exit_approval_process,
            "exit_interview",
            existing,
        )
        return {
            "status": "info",
            "message": _("Exit Interview record already exists."),
        }
    doc = frappe.get_doc("Exit Approval Process", exit_approval_process)
    today_date = getdate(today())
    date_str = doc.custom_exit_questionnaire_notification_date
    notif_date = datetime.strptime(date_str, "%d-%m-%Y").strftime("%Y-%m-%d")

    if getdate(notif_date) > today_date:
        return {
            "status": "info",
            "message": _("Exit Interview notification will be sent on {0}").format(
                formatdate(notif_date)
            ),
        }

    return create_exit_interview(employee, company, exit_approval_process)


# ? FUNCTION TO CREATE EXIT INTERVIEW
def create_exit_interview(employee, company, exit_approval_process):
    # ? RETURN IF ALREADY EXISTS
    if frappe.db.exists("Exit Interview", {"employee": employee}):
        send_exit_interview_notification(employee)
        return {
            "status": "info",
            "message": _("Exit Interview already exists. Email resent."),
        }

    # ? DETERMINE QUIZ FIELD BASED ON COMPANY
    prompt_company = get_prompt_company_name().get("company_name")
    indifoss_company = get_indifoss_company_name().get("company_name")

    if company == prompt_company:
        quiz_field = "custom_exit_interview_quiz_prompt"
    elif company == indifoss_company:
        quiz_field = "custom_exit_interview_quiz_indifoss"
    else:
        frappe.throw(_("Company not recognized or quiz not configured."))

    # ? FETCH QUIZ
    quiz_name = frappe.db.get_value("HR Settings", None, quiz_field)
    if not quiz_name:
        frappe.throw(_("Exit quiz not configured for this company."))

    # ? CREATE EXIT INTERVIEW DOCUMENT
    doc = frappe.new_doc("Exit Interview")
    doc.update(
        {
            "employee": employee,
            "company": company,
            "date": nowdate(),
            "custom_resignation_quiz": quiz_name,
        }
    )
    doc.insert(ignore_permissions=True)
    frappe.db.commit()
    message = f"Exit Interview created"
    # ? SEND EMAIL + LINK TO EXIT APPROVAL
    try:
        send_exit_interview_notification(employee, doc.name)
        message += " and email sent"
    except Exception as e:
        message += " and Error while Sending Email"
    frappe.db.set_value(
        "Exit Approval Process", exit_approval_process, "exit_interview", doc.name
    )

    return {
        "status": "success",
        "message": message,
    }


# ? SEND EXIT INTERVIEW EMAIL
@frappe.whitelist()
def send_exit_interview_notification(employee, exit_interview_name=None, send_from_button=0):
    try:
        enable_exit_emails = frappe.db.get_single_value("HR Settings", "custom_enable_exit_mails") or 0
    except Exception as e:
        frappe.log_error(message=str(e), title="Error fetching HR Settings - custom_enable_exit_mails")
        enable_exit_emails = 0

    user_id = frappe.db.get_value("Employee", employee, "user_id")
    if not user_id:
        frappe.throw(_("Employee does not have a User ID."))

    if not exit_interview_name:
        exit_interview_name = frappe.db.get_value(
            "Exit Interview", {"employee": employee}
        )

    # ? SEND EMAILS ONLY IF IT IS CALLED FROM BUTTON OR EXIT MAIL ENABLE IN HR SETTINGS
    if send_from_button or enable_exit_emails:
        send_notification_email(
            doctype="Exit Interview",
            docname=exit_interview_name,
            recipients=[user_id],
            notification_name="Exit Questionnaire Mail To Employee",
            button_link=frappe.utils.get_url()
            + "/login?redirect-to=/exit-questionnaire/new#login",
        )

    return {"status": "success", "message": _("Exit Interview email sent.")}

# ? FUNCTION TO VALIDATE APPROVAL STATUS
def validate_approval_status(doc):

    # ? VALIDATE APPROVAL STATUS
    if doc.resignation_approval not in ["Approved","Rejected", "Approved by Reporting Manager", "Pending"]:
            frappe.throw(_("Resignation Approval must be either 'Pending','Approved', 'Rejected' or 'Approved by Reporting Manager'"))