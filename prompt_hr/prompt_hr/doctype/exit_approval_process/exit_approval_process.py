# Copyright (c) 2025, Jignasha Chavda and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document
from frappe import _
from frappe.utils import nowdate, today, add_days, getdate, formatdate
from prompt_hr.py.utils import (
    send_notification_email,
    get_hr_managers_by_company,
    get_prompt_company_name,
    get_indifoss_company_name,
)


# ? MAIN EXIT APPROVAL CLASS
class ExitApprovalProcess(Document):
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


# ? RAISE EXIT CHECKLIST OR SCHEDULE IT
@frappe.whitelist()
def raise_exit_checklist(employee, company, exit_approval_process):
    doc = frappe.get_doc("Exit Approval Process", exit_approval_process)
    today_date = getdate(today())
    notif_date = doc.custom_exit_checklist_notification_date

    # ? CALCULATE NOTIFICATION DATE IF NOT SET
    if not notif_date:
        field = (
            "custom_days_before_exit_checklist_prompt"
            if company == get_prompt_company_name()
            else "custom_days_before_exit_checklist_indifoss"
        )
        days = frappe.db.get_value("HR Settings", None, field) or 0
        notif_date = add_days(doc.last_date_of_working, -int(days))
        frappe.db.set_value(
            "Exit Approval Process",
            exit_approval_process,
            "custom_exit_checklist_notification_date",
            notif_date,
        )

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
            doc.append("activities", act)

    # ? FETCH RECIPIENTS (HR + ACTIVITY USERS/ROLES)
    recipients = set(get_hr_managers_by_company(company))
    valid_users = {
        e.user_id
        for e in frappe.get_all("Employee", {"company": company}, ["user_id"])
        if e.user_id
    }

    role_users = {act.user for act in doc.activities if act.user} | {
        u.parent
        for act in doc.activities
        if act.role
        for u in frappe.get_all("Has Role", {"role": act.role}, ["parent"])
    }

    recipients |= {
        u.email
        for u in frappe.get_all(
            "User", {"name": ["in", list(role_users & valid_users)]}, ["email"]
        )
        if u.email
    }

    doc.insert(ignore_permissions=True)
    frappe.db.commit()
    send_notification_email(
        doctype="Employee Separation",
        docname=doc.name,
        recipients=list(recipients),
        notification_name="Employee Separation Notification",
    )
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
    doc = frappe.get_doc("Exit Approval Process", exit_approval_process)
    today_date = getdate(today())
    notif_date = doc.custom_exit_questionnaire_notification_date

    if not notif_date:
        field = (
            "custom_days_before_exit_questionnaire_prompt"
            if company == "Prompt"
            else "custom_days_before_exit_questionnaire_indifoss"
        )
        days = frappe.db.get_value("HR Settings", None, field) or 0
        notif_date = add_days(doc.last_date_of_working, -int(days))
        frappe.db.set_value(
            "Exit Approval Process",
            exit_approval_process,
            "custom_exit_questionnaire_notification_date",
            notif_date,
        )

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

    # ? SEND EMAIL + LINK TO EXIT APPROVAL
    send_exit_interview_notification(employee, doc.name)
    frappe.db.set_value(
        "Exit Approval Process", exit_approval_process, "exit_interview", doc.name
    )

    return {
        "status": "success",
        "message": _("Exit Interview created and email sent."),
    }


# ? SEND EXIT INTERVIEW EMAIL
@frappe.whitelist()
def send_exit_interview_notification(employee, exit_interview_name=None):
    user_id = frappe.db.get_value("Employee", employee, "user_id")
    if not user_id:
        frappe.throw(_("Employee does not have a User ID."))

    if not exit_interview_name:
        exit_interview_name = frappe.db.get_value(
            "Exit Interview", {"employee": employee}
        )

    send_notification_email(
        doctype="Exit Interview",
        docname=exit_interview_name,
        recipients=[user_id],
        notification_name="Exit Questionnaire Mail To Employee",
        button_link=frappe.utils.get_url() + "/login?redirect-to=/candidate-portal/new#login"
    )
    return {"status": "success", "message": _("Exit Interview email sent.")}
