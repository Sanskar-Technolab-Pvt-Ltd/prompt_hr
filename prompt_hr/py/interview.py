

import frappe
from prompt_hr.py.utils import send_notification_email
from frappe.utils import now_datetime, add_to_date, get_datetime, format_time
from datetime import datetime, time

from frappe.utils import formatdate, format_time
from frappe import _

# ? FUNCTION TO UPDATE EXPECTED SCORE BASED ON INTERVIEW ROUND
def before_save(doc, method):

    if doc.is_new():
        expected_score = frappe.db.get_value("Interview Round",doc.interview_round, "custom_expected_average_score")
        if doc.custom_expected_average_score != expected_score:
            doc.custom_expected_average_score = expected_score


@frappe.whitelist()
def send_interview_reminder_to_interviewer(interviewer_employee, interview_name, job_applicant, interview_round, external=0):
    """
    #! SEND REMINDER MAIL TO INTERVIEWER IF FEEDBACK NOT SUBMITTED
    """
    try:
        print(interviewer_employee, interview_name, job_applicant, interview_round, external)
        #? FETCH EMPLOYEE EMAIL
        if external:
            interviewer_email = frappe.db.get_value("Supplier", interviewer_employee, "custom_user")

        else:
            interviewer_email = frappe.db.get_value("Employee", interviewer_employee, "prefered_email")
            print("interviewer_email", interviewer_email)
            if not interviewer_email:
                interviewer_email = frappe.db.get_value("Employee", interviewer_employee, "user_id")

        if not interviewer_email:
            return "⚠️ No email found for the interviewer."

        if external:
            existing_feedback = frappe.db.exists(
                "Interview Feedback",
                {
                    "interview": interview_name,
                    "interviewer": frappe.db.get_value("Supplier", interviewer_employee, "custom_user"),
                    "docstatus": 1
                }
            )
            print(existing_feedback)
        else:
            #? CHECK IF FEEDBACK ALREADY SUBMITTED
            existing_feedback = frappe.db.exists(
                "Interview Feedback",
                {
                    "interview": interview_name,
                    "interviewer": frappe.db.get_value("Employee", interviewer_employee, "user_id"),
                    "docstatus": 1
                }
            )

        if existing_feedback:
            return f"✅ Feedback already submitted by {interviewer_employee}. No reminder sent."

        #? SEND EMAIL REMINDER
        send_notification_email(
            recipients=[interviewer_email],
            notification_name="Interview Feedback Reminder",  # Notification Doctype Name
            doctype="Interview",
            docname=interview_name,
            send_link=False,
            fallback_subject=f"Reminder: Submit Interview Feedback for {job_applicant} ({interview_round})",
            fallback_message=f"""
                <p>Dear Interviewer,</p>

                <p>This is a gentle reminder regarding the interview for <b>{job_applicant}</b> (Round: <b>{interview_round}</b>).</p>

                <p>Please ensure that you have submitted your interview feedback at the earliest.</p>

                <p>You can submit it directly from your Interview record:
                <br><a href="{frappe.utils.get_url()}/app/interview/{interview_name}" target="_blank">
                Click here to open the interview</a></p>

                <br>
                <p>Thank you for your time and contribution to the hiring process.</p>
                <p>Warm regards,<br>
                <b>HR Team</b></p>
            """,
            send_header_greeting=True,
        )

        return f"📧 Reminder sent successfully to <b>{interviewer_employee}</b> ({interviewer_email})."

    except Exception as e:
        #? LOG ERROR TO Frappe ERROR LOG
        frappe.log_error(
            message=frappe.get_traceback(),
            title=f"Interview Reminder Failed for {interviewer_employee}"
        )
        return f"Failed to send reminder to {interviewer_employee}. Error: {str(e)}"

@frappe.whitelist()
def interviewer_reschedule_interview(docname, scheduled_on, from_time, to_time):
    """Reschedule interview and notify all internal interviewers using Notification DocType."""

    # 1 Fetch Interview document
    doc = frappe.get_doc("Interview", docname)

    # 2 Get all internal interviewer employees
    interviewer_employees = [
        row.custom_interviewer_employee
        for row in (doc.interview_details or [])
        if row.custom_interviewer_employee
    ]

    # 3  Fetch user emails linked to those employees
    interviewer_emails = []
    for emp in interviewer_employees:
        user_id = frappe.db.get_value("Employee", emp, "user_id")
        if user_id:
            email = frappe.db.get_value("User", user_id, "email")
            if email:
                interviewer_emails.append(email)

    external_emails = []

    for row in (doc.custom_external_interviewers or []):
        if row.custom_user:
            # Get email directly from Supplier's custom_user field
            email = frappe.db.get_value("Supplier", row.custom_user, "custom_user")
            if email:
                external_emails.append(email)

    # Combine both lists and remove duplicates
    all_recipients = list(set(interviewer_emails + external_emails))

    # 4  Remove duplicates
    interviewer_emails = list(set(interviewer_emails))

    # 5 Update interview schedule
    doc.scheduled_on = scheduled_on
    doc.from_time = from_time
    doc.to_time = to_time
    # doc.save(ignore_permissions=True)
    # frappe.db.commit()

    # 6  Send email using Notification (instead of direct sendmail)
    if all_recipients:
        try:
            # 🔸 You must create a Notification in your system with name "Interview Rescheduled Notification"
            # and set it to be "For Doctype = Interview"
            # and use Jinja fields like {{ doc.custom_applicant_name }}, {{ doc.scheduled_on }}, etc.
            notification_name = "Interview Rescheduled Notification"

            notification = frappe.get_doc("Notification", notification_name)
            subject = frappe.render_template(notification.subject, {"doc": doc})
            message = frappe.render_template(notification.message, {"doc": doc})
            
            frappe.sendmail(
                recipients=all_recipients,
                subject=subject,
                message=message,
            )
        except frappe.DoesNotExistError:
            frappe.log_error("Notification 'Interview Rescheduled Notification' not found.")
        except Exception as e:
            frappe.log_error(f"Error sending interview reschedule notification: {str(e)}")

    return _("Interview rescheduled successfully and notification sent to interviewers.")


def send_interview_feedback_notifications():
    """
    #! SEND EMAIL NOTIFICATIONS FOR INTERVIEWS COMPLETED IN LAST 15 MINUTES
    #? 1. SEND THANK-YOU EMAIL TO CANDIDATES
    #? 2. SEND FEEDBACK REMINDER EMAIL TO INTERVIEWERS (INTERNAL + EXTERNAL)
    """
    try:
        #! DEFINE CURRENT TIME AND 15 MINUTES AGO
        current_time = now_datetime()
        fifteen_min_ago = add_to_date(current_time, minutes=-15)

        #? FETCH INTERVIEWS WHICH ARE ACTIVE (DOCSTATUS = 0)
        interviews = frappe.get_all(
            "Interview",
            filters={"docstatus": 0},
            fields=["name", "job_applicant", "scheduled_on", "to_time"]
        )
        if not interviews:
            frappe.logger().info("ℹ️ No active interviews found.")
            return

        for interview in interviews:
            #! VALIDATE AND COMBINE DATE + TIME INTO A SINGLE DATETIME
            if not (interview.scheduled_on and interview.to_time):
                continue

            if isinstance(interview.to_time, str):
                try:
                    to_time_obj = datetime.strptime(interview.to_time, "%H:%M:%S").time()
                except Exception:
                    frappe.logger().warning(f"⚠️ Invalid time format for {interview.name}: {interview.to_time}")
                    continue
            else:
                try:
                    to_time_str = str(interview.to_time)
                    to_time_obj = datetime.strptime(to_time_str, "%H:%M:%S").time()
                except:
                    frappe.logger().warning(f"⚠️ Invalid time format for {interview.name}: {interview.to_time}")
                    continue
                    

            scheduled_datetime = datetime.combine(interview.scheduled_on, to_time_obj)
            #? SKIP IF NOT WITHIN LAST 15 MINUTES
            if not (fifteen_min_ago <= scheduled_datetime <= current_time):
                continue

            #! FETCH CANDIDATE EMAIL
            candidate_email = frappe.db.get_value("Job Applicant", interview.job_applicant, "email_id")
            #! FETCH INTERNAL INTERVIEWERS (EMPLOYEE-BASED)
            internal_interviewers = frappe.get_all(
                "Interview Detail",
                filters={"parent": interview.name},
                pluck="custom_interviewer_employee"
            )

            internal_emails = []
            if internal_interviewers:
                internal_emails = frappe.get_all(
                    "Employee",
                    filters={"name": ["in", internal_interviewers], "status": "Active"},
                    pluck="user_id"
                )

            #! FETCH EXTERNAL INTERVIEWERS (SUPPLIER-BASED)
            external_interviewers = frappe.get_all(
                "External Interviewer",
                filters={"parent": interview.name},
                pluck="custom_user"
            )

            external_emails = []
            if external_interviewers:
                external_emails = frappe.get_all(
                    "Supplier",
                    filters={"name": ["in", external_interviewers], "disabled": 0},
                    pluck="custom_user"
                )
            #! MERGE ALL INTERVIEWER EMAILS (REMOVE DUPLICATES)
            email_ids = list({email for email in (internal_emails + external_emails) if email})

            #! SEND THANK-YOU EMAIL TO CANDIDATE
            if candidate_email:
                send_notification_email(
                    recipients=[candidate_email],
                    notification_name="Interview Thank You Notification",  # Notification Doctype Name
                    doctype="Interview",
                    docname=interview.name,
                    send_link=False,
                    fallback_subject=f"Thank You for Attending Interview",
                    fallback_message=f"""
                        <p>Dear {{interview.custom_applicant_name}},<br><br></p>

                            <p>Thank you for attending your interview scheduled on 
                            <b>{{ frappe.utils.format_date(interview.scheduled_on) }} between {{interview.from_time}} - {{interview.to_time}}</b>.<br></p>

                            <p>We appreciate your time and interest.<br><br></p>

                            <p>Regards,<br>
                            Recruitment Team</p>
                    """,
                )

            #! SEND FEEDBACK REMINDER EMAIL TO INTERVIEWERS
            if email_ids:
                #? SEND EMAIL REMINDER
                send_notification_email(
                    recipients=email_ids,
                    notification_name="Interview Feedback Reminder",  # Notification Doctype Name
                    doctype="Interview",
                    docname=interview.name,
                    send_link=False,
                    fallback_subject=f"Reminder: Submit Interview Feedback for {interview.custom_applicant_name} ({interview.interview_round})",
                    fallback_message=f"""
                        <p>Dear Interviewer,</p>

                        <p>This is a gentle reminder regarding the interview for <b>{interview.custom_applicant_name}</b> (Round: <b>{interview.interview_round}</b>).</p>

                        <p>Please ensure that you have submitted your interview feedback at the earliest.</p>

                        <p>You can submit it directly from your Interview record:
                        <br><a href="{frappe.utils.get_url()}/app/interview/{interview.name}" target="_blank">
                        Click here to open the interview</a></p>

                        <br>
                        <p>Thank you for your time and contribution to the hiring process.</p>
                        <p>Warm regards,<br>
                        <b>HR Team</b></p>
                    """,
                    send_header_greeting=True,
                )
        frappe.db.commit()

    except Exception as error:
        frappe.log_error("Error Sending Interview Feedback Notifications", str(error))
