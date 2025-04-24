import frappe
import traceback
from dateutil.relativedelta import relativedelta
from frappe.utils import getdate, nowdate, formatdate

# ! prompt_hr.py.job_opening.send_job_opening_notification

@frappe.whitelist()
def send_job_opening_notification(
    due_date=None,
    notification_name=None,
    min_tenure_in_company=0,
    min_tenure_in_current_role=0,
    allowed_department=None,
    allowed_location=None,
    allowed_grade=None,
    job_opening=None,
    source=None
):
    """
    Send internal job opening notifications to eligible employees.
    """
    try:
        # Build employee filters
        filters = {"status": "Active"}
        if allowed_department:
            filters["department"] = ["in", allowed_department]
        if allowed_location:
            filters["location"] = ["in", allowed_location]
        if allowed_grade:
            filters["grade"] = ["in", allowed_grade]

        # Fetch employees
        employees = frappe.get_all(
            "Employee",
            filters=filters,
            fields=["name", "date_of_joining", "personal_email", "user_id"]
        )

        # Build role history map for tenure calculation
        role_history_map = get_role_history_map()
        eligible_emails = []

        # Filter by tenure in company and role
        for emp in employees:
            if not emp.date_of_joining:
                continue
            company_months = get_months_between(emp.date_of_joining, nowdate())
            if company_months < float(min_tenure_in_company):
                continue
            role_months = get_role_tenure_from_map(role_history_map, emp.name, emp.date_of_joining)
            if role_months < float(min_tenure_in_current_role):
                continue
            if emp.user_id:
                eligible_emails.append(emp.user_id)

        # Send notification if anyone is eligible
        if eligible_emails:
            send_notification_email(
                emails=eligible_emails,
                due_date=due_date,
                notification_name=notification_name,
                job_opening=job_opening,
                source=source
            )

        return eligible_emails

    except Exception as e:
        frappe.log_error(
            title="Job Notification Error",
            message=f"Error in job notification: {str(e)}\n{traceback.format_exc()}"
        )
        return []


def get_months_between(from_date, to_date):
    if not from_date or not to_date:
        return 0
    from_dt = getdate(from_date)
    to_dt = getdate(to_date)
    diff = relativedelta(to_dt, from_dt)
    return diff.years * 12 + diff.months


def get_role_history_map():
    records = frappe.get_all(
        "Employee Internal Work History",
        fields=["parent", "from_date", "to_date"],
        order_by="to_date desc"
    )
    history_map = {}
    for row in records:
        history_map.setdefault(row.parent, []).append(row)
    return history_map


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
            title="Role Tenure Error",
            message=f"Error getting role tenure for {emp_id}: {str(e)}\n{traceback.format_exc()}"
        )
        return 0


def send_notification_email(emails, due_date=None, notification_name=None, job_opening=None, source=None):
    """
    Render and send notification emails based on a Notification template or fallback.
    """
    try:
        # Fetch Notification document if provided
        notification_doc = None
        if notification_name:
            rec = frappe.get_all(
                "Notification",
                filters={"name": notification_name},
                limit=1
            )
            if rec:
                notification_doc = frappe.get_doc("Notification", rec[0].name)

        # Fetch the Job Opening document for context
        job_doc = None
        if job_opening:
            try:
                job_doc = frappe.get_doc("Job Opening", job_opening)
            except frappe.DoesNotExistError:
                job_doc = None

        base_url = frappe.utils.get_url()
        apply_link = (
            f"{base_url}/app/job-applicant/new-job-applicant-1"
            f"?job_title={job_opening}&source={source}"
        )

        for email in emails:
            # Build template context
            context = {
                "doc": job_doc or frappe._dict({}),
                "user": email,
                "apply_link": apply_link
            }

            if notification_doc:
                subject = frappe.render_template(notification_doc.subject, context)
                message = frappe.render_template(notification_doc.message, context)
            else:
                # Fallback subject and message
                subject = "New Internal Job Opening – Apply Now!"
                formatted_due = formatdate(due_date) if due_date else ''
                message = (
                    f"<p>A new job opportunity is available until <b>{formatted_due}</b>.</p>"
                    f"<p>Please check the portal for more information.</p>"
                )

            # Append common call-to-action
            message += (
                "<hr>"
                "<p>Click below to apply:</p>"
                f"<p><a href=\"{apply_link}\" target=\"_blank\">Apply Now</a></p>"
            )

            # Send the email
            frappe.sendmail(
                recipients=[email],
                subject=subject,
                message=message
            )

        frappe.log_error(
            title="Job Notification Sent",
            message=f"Sent job opening email to {len(emails)} employees."
        )

    except Exception as e:
        frappe.log_error(
            title="Notification Email Error",
            message=f"Failed sending notification: {str(e)}\n{traceback.format_exc()}"
        )
