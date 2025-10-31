# Copyright (c) 2025, Jignasha Chavda and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document
from prompt_hr.py.utils import get_roles_from_hr_settings_by_module, get_email_ids_for_roles, send_notification_email


class CandidatePortal(Document):
    def on_update(self):
        # GET RECRUITER ROLES FROM HR SETTINGS
        if frappe.flags.in_web_form:
            return
        try:
            recruiter_roles = get_roles_from_hr_settings_by_module("custom_hr_roles_for_recruitment")
        except Exception:
            recruiter_roles = []

        # COLLECT RECRUITER EMAILS
        recruiter_emails = get_email_ids_for_roles(recruiter_roles) if recruiter_roles else []
        candidate_email = None
        # CANDIDATE EMAIL (FIELD IN YOUR DOC)
        if self.applicant_email:
            candidate_email = frappe.db.get_value("Job Applicant", self.applicant_email, "email_id")

        if candidate_email:
            #  CALL NOTIFICATION DOCTYPE
            send_notification_email(
                recipients=[candidate_email],
                notification_name="Candidate Portal Update Notification To Candidate",  # Notification Doctype Name
                doctype="Candidate Portal",
                docname=self.name,
                send_link=False,
                fallback_subject=f"Candidate Portal Updated - {{ doc.applicant_name }}",
                fallback_message=f"""
                    Dear {{  doc.applicant_name }},<br><br>

                    Your Candidate Portal has been updated. You can log in and review the latest changes.<br><br>

                    <b>Details:</b><br>
                    - Candidate Name: {{ doc.applicant_name }}<br>
                    - Updated On: {{ frappe.utils.format_datetime(doc.modified) }}<br><br>

                    Regards,<br>
                    HR Team
                """,
                send_header_greeting=False,
            )

        if recruiter_emails:
            #  CALL NOTIFICATION DOCTYPE
            send_notification_email(
                    recipients=recruiter_emails,
                    notification_name="Candidate Portal Update Notification",  # Notification Doctype Name
                    doctype="Candidate Portal",
                    docname=self.name,
                    send_link=False,
                    fallback_subject=f"Candidate Portal Updated - {{ doc.applicant_name }}",
                    fallback_message=f"""
                            Hello Recruiter,<br><br>

                            The Candidate Portal for <b>{{ doc.applicant_name }}</b> has been updated.<br>
                            Please review the changes at your convenience.<br><br>

                            Regards,<br>
                            HR Team
                    """,
                    send_header_greeting=True,
                )

# ? SEND NOTIFICATION EMAIL TO HR FROM TEMPLATE
def send_notification_to_hr(notification_name, job_offer_name, recipient):
    try:
        notification = frappe.get_doc("Notification", notification_name)
        context = {"doc": {"name": job_offer_name}, "user": recipient}

        subject = frappe.render_template(notification.subject, context)
        message = frappe.render_template(notification.message, context)

        base_url = frappe.utils.get_url()
        message += f"""
            <hr>
            <p><b>View Job Offer:</b> 
            <a href="{base_url}/app/job-offer/{job_offer_name}" target="_blank">{job_offer_name}</a></p>
        """

        frappe.sendmail(
            recipients=[recipient],
            subject=subject,
            message=message,
        )

    except Exception:
        frappe.log_error(
            frappe.get_traceback(), f"{notification_name} Notification Error"
        )
