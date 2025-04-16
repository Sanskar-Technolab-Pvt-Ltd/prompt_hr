import frappe
import traceback
from dateutil.relativedelta import relativedelta
from frappe.utils import getdate, nowdate


# ? RELEASE INTERNAL JOB POSTING TO ELIGIBLE EMPLOYEES
@frappe.whitelist()
def release_internal_job_posting(
    due_date,
    min_tenure_in_company=0,
    min_tenure_in_current_role=0,
    allowed_department=None,
    allowed_location=None,
    allowed_grade=None,
    notification_name=None,
    job_opening=None,
):
    try:
        filters = {"status": "Active"}

        if allowed_department:
            filters["department"] = ["in", allowed_department]
        if allowed_location:
            filters["location"] = ["in", allowed_location]
        if allowed_grade:
            filters["grade"] = ["in", allowed_grade]

        employees = frappe.get_all(
            "Employee",
            filters=filters,
            fields=["name", "date_of_joining", "personal_email"],
        )

        role_history_map = get_role_history_map()
        eligible_emails = []

        for emp in employees:
            if not emp.date_of_joining:
                continue

            company_months = get_months_between(emp.date_of_joining, nowdate())
            if company_months < float(min_tenure_in_company):
                continue

            role_months = get_role_tenure_from_map(
                role_history_map, emp.name, emp.date_of_joining
            )
            if role_months < float(min_tenure_in_current_role):
                continue

            if emp.personal_email:
                eligible_emails.append(emp.personal_email)

        if eligible_emails:
            job_opening_doc = frappe.get_doc("Job Opening", job_opening)
            send_notification_from_template(
                eligible_emails, notification_name, doc=job_opening_doc
            )

        return eligible_emails

    except Exception as e:
        frappe.log_error(
            title="Internal Job Posting Error",
            message=f"Error releasing internal job posting: {str(e)}\n{traceback.format_exc()}",
        )
        return []


# ? SEND JOB REFERRAL EMAIL TO ALL ACTIVE EMPLOYEES
@frappe.whitelist()
def notify_all_employees_for_referral(job_opening, notification_name=None):
    try:
        employees = frappe.get_all(
            "Employee", filters={"status": "Active"}, fields=["name", "personal_email"]
        )

        referral_emails = [
            emp.personal_email for emp in employees if emp.personal_email
        ]

        if referral_emails:
            job_opening_doc = frappe.get_doc("Job Opening", job_opening)
            send_notification_from_template(
                referral_emails, notification_name, doc=job_opening_doc
            )
            return f"Referral email sent to {len(referral_emails)} employees."
        return "No valid emails found."

    except Exception as e:
        frappe.log_error(
            title="Referral Notification Error",
            message=f"Error while sending referral notification: {str(e)}\n{traceback.format_exc()}",
        )
        return "An error occurred while sending referral emails."


# ? HELPER: CALCULATE MONTH DIFFERENCE
def get_months_between(from_date, to_date):
    if not from_date or not to_date:
        return 0
    from_dt = getdate(from_date)
    to_dt = getdate(to_date)
    diff = relativedelta(to_dt, from_dt)
    return diff.years * 12 + diff.months


# ? HELPER: GET ROLE HISTORY MAP {employee_name: [history]}
def get_role_history_map():
    records = frappe.get_all(
        "Employee Internal Work History",
        fields=["parent", "from_date", "to_date"],
        order_by="to_date desc",
    )
    history_map = {}
    for row in records:
        history_map.setdefault(row.parent, []).append(row)
    return history_map


# ? HELPER: GET TENURE IN CURRENT ROLE
def get_role_tenure_from_map(history_map, emp_id, joining_date):
    try:
        if emp_id in history_map and history_map[emp_id]:
            latest = history_map[emp_id][0]
            from_date = latest.from_date
            to_date = latest.to_date or nowdate()
            return get_months_between(from_date, to_date)

        return get_months_between(joining_date, nowdate())

    except Exception as e:
        frappe.log_error(
            title="Role Tenure Calc Error",
            message=f"Error calculating role tenure for {emp_id}: {str(e)}\n{traceback.format_exc()}",
        )
        return 0


# ? GENERIC HELPER: SEND EMAIL USING NOTIFICATION TEMPLATE
def send_notification_from_template(emails, notification_name, doc=None):
    try:
        notification_doc = frappe.get_doc("Notification", notification_name)

        for email in emails:
            context = {"doc": doc or frappe._dict({}), "user": email}

            subject = frappe.render_template(notification_doc.subject, context)
            message = frappe.render_template(notification_doc.message, context)

            if doc and doc.doctype and doc.name:
                link = f"{frappe.utils.get_url()}/app/{doc.doctype.replace(' ', '-').lower()}/{doc.name}"
                message += (
                    f"<br><br><a href='{link}'>Click here to view the Job Opening</a>"
                )

            frappe.sendmail(recipients=[email], subject=subject, message=message)

        frappe.log_error(
            title="Notification Sent",
            message=f"Notification '{notification_name}' sent to {len(emails)} employees.",
        )

    except Exception as e:
        frappe.log_error(
            title="Notification Sending Failed",
            message=f"Failed to send '{notification_name}': {str(e)}\n{traceback.format_exc()}",
        )


import frappe
import json

@frappe.whitelist()
def add_to_interview_availability(job_openings, employees):
    job_openings = json.loads(job_openings) if isinstance(job_openings, str) else job_openings
    employees = json.loads(employees) if isinstance(employees, str) else employees

    for job_opening in job_openings:

        # ? CREATE INTERVIEW AVAILABILITY DOCUMENT
        interview_doc = frappe.new_doc("Interview Availability Form")
        interview_doc.job_opening = job_opening
        interview_doc.for_designation = "Accountant"

        # for emp in employees:

        #     # ? ADD EACH SELECTED EMPLOYEE TO THE CHILD TABLE
        #     interview_doc.append("employees", {
        #         "employee": emp
        #     })

        interview_doc.insert(ignore_permissions=True)  

        # ? SHARE THE INTERVIEW AVAILABILITY WITH EACH EMPLOYEE'S USER
        for emp in employees:
            user = frappe.db.get_value("Employee", emp, "user_id")
            if user:
                try:
                    frappe.share.add(
                        doctype=interview_doc.doctype,
                        name=interview_doc.name,
                        user=user,
                        read=1,
                        write=0,
                        share=0,
                    )
                except Exception as e:
                    frappe.log_error(f"Sharing failed for {emp} ({user}): {str(e)}", "Interview Availability Share Error")

    return "Interview Availability records created and shared successfully."
