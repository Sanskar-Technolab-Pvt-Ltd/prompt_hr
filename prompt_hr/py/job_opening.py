import frappe
import traceback
from dateutil.relativedelta import relativedelta
from frappe.utils import getdate, nowdate

# ? FUNCTION TO RELEASE INTERNAL JOB POSTING


@frappe.whitelist()
def release_internal_job_posting(
    due_date,
    min_tenure_in_company=0,
    min_tenure_in_current_role=0,
    allowed_department=None,
    allowed_location=None,
    allowed_grade=None,
):
    try:
        # ? BASE FILTER FOR ACTIVE EMPLOYEES
        filters = {"status": "Active"}

        # ? APPLY STATIC FILTERS
        if allowed_department:
            filters["department"] = ["in", allowed_department]
        if allowed_location:
            filters["location"] = ["in", allowed_location]
        if allowed_grade:
            filters["grade"] = ["in", allowed_grade]

        # ? FETCH EMPLOYEES BASED ON STATIC FILTERS
        employees = frappe.get_all(
            "Employee",
            filters=filters,
            fields=["name", "date_of_joining", "personal_email"],
        )

        # ? FETCH WORK HISTORY FOR ALL EMPLOYEES IN ONE GO
        role_history_map = get_role_history_map()

        eligible_emails = []

        for emp in employees:
            if not emp.date_of_joining:
                continue

            # ? CHECK TENURE IN COMPANY
            company_months = get_months_between(emp.date_of_joining, nowdate())
            if company_months < float(min_tenure_in_company):
                continue

            # ? CHECK TENURE IN CURRENT ROLE FROM HISTORY
            role_months = get_role_tenure_from_map(
                role_history_map, emp.name, emp.date_of_joining
            )
            if role_months < float(min_tenure_in_current_role):
                continue

            # ? FINAL ELIGIBILITY - VALID EMAIL ONLY
            if emp.personal_email:
                eligible_emails.append(emp.personal_email)

        # ? SEND EMAIL IF THERE ARE ANY ELIGIBLE EMPLOYEES
        if eligible_emails:
            send_existing_notification(eligible_emails, due_date)

        return eligible_emails

    except Exception as e:
        frappe.log_error(
            title="Internal Job Posting Error",
            message=f"Error releasing internal job posting: {str(e)}\n{traceback.format_exc()}",
        )
        return []


# ? FUNCTION TO GET MONTH DIFFERENCE BETWEEN TWO DATES
def get_months_between(from_date, to_date):
    if not from_date or not to_date:
        return 0
    from_dt = getdate(from_date)
    to_dt = getdate(to_date)
    diff = relativedelta(to_dt, from_dt)
    return diff.years * 12 + diff.months


# ? FUNCTION TO BUILD A HASHMAP OF WORK HISTORY PER EMPLOYEE
def get_role_history_map():
    records = frappe.get_all(
        "Employee Internal Work History",
        fields=["parent", "from_date", "to_date"],
        order_by="to_date desc",
    )

    # ? BUILD HASHMAP: {employee_name: [latest_record, ...]}
    history_map = {}
    for row in records:
        history_map.setdefault(row.parent, []).append(row)
    return history_map


# ? FUNCTION TO GET TENURE FROM HISTORY OR FALLBACK TO JOINING DATE
def get_role_tenure_from_map(history_map, emp_id, joining_date):
    try:
        if emp_id in history_map and history_map[emp_id]:
            latest = history_map[emp_id][0]
            from_date = latest.from_date
            to_date = latest.to_date or nowdate()
            return get_months_between(from_date, to_date)

        # ? FALLBACK TO COMPANY JOINING DATE
        return get_months_between(joining_date, nowdate())

    except Exception as e:
        frappe.log_error(
            title="Role Tenure Calc Error",
            message=f"Error calculating role tenure for {emp_id}: {str(e)}\n{traceback.format_exc()}",
        )
        return 0


# ? FUNCTION TO SEND EMAIL TO ELIGIBLE EMPLOYEES
def send_existing_notification(emails, due_date):
    try:
        # ? TRY FETCHING A NOTIFICATION TEMPLATE FOR EMPLOYEE TYPE
        notification_doc = None
        notification_list = frappe.get_all(
            "Notification",
            filters={"document_type": "Employee", "channel": "Email", "enabled": 1},
            limit=1,
        )

        if notification_list:
            notification_doc = frappe.get_doc("Notification", notification_list[0].name)

        subject = "Internal Job Opening"
        base_url = frappe.utils.get_url()
        apply_link = f"{base_url}/app/job-applicant/new-job-applicant-1"

        if notification_doc:
            for email in emails:
                context = {"doc": frappe._dict({}), "user": email}
                rendered_subject = frappe.render_template(
                    notification_doc.subject, context
                )
                rendered_message = frappe.render_template(
                    notification_doc.message, context
                )

                rendered_message += f"""
                    <hr>
                    <p><b>Interested?</b> You can apply directly using the link below:</p>
                    <p><a href="{apply_link}" target="_blank">Apply for this Job</a></p>
                """

                frappe.sendmail(
                    recipients=[email],
                    subject=rendered_subject,
                    message=rendered_message,
                )
        else:
            # ? FALLBACK MESSAGE
            message = f"""
                <p>A new internal job opportunity is open until <b>{due_date}</b>.</p>
                <p>Please check the portal for details.</p>
                <hr>
                <p><b>Interested?</b> You can apply directly using the link below:</p>
                <p><a href="{apply_link}" target="_blank">Apply for this Job</a></p>
            """

            frappe.sendmail(recipients=emails, subject=subject, message=message)

        frappe.log_error(
            title="Job Opening Notification Sent",
            message=f"Notification sent to {len(emails)} employees.",
        )

    except Exception as e:
        frappe.log_error(
            title="Job Opening Notification Error",
            message=f"Error sending job opening notification: {str(e)}\n{traceback.format_exc()}",
        )
