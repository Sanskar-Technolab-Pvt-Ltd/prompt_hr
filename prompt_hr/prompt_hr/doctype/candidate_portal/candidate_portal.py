# Copyright (c) 2025, Jignasha Chavda and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document


class CandidatePortal(Document):
    pass


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
