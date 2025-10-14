

import frappe
from prompt_hr.py.utils import send_notification_email

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
