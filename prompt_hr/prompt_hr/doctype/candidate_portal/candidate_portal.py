# Copyright (c) 2025, Jignasha Chavda and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document


class CandidatePortal(Document):

    def on_update(self):
        # ? SYNC EXPECTED DOJ TO JOB OFFER IF CHANGED
        if self.has_value_changed("expected_date_of_joining") and self.job_offer:
            try:
                frappe.db.set_value(
                    "Job Offer",
                    self.job_offer,
                    "custom_expected_date_of_joining",
                    self.expected_date_of_joining
                )

                hr_email = frappe.db.get_value("Job Offer", self.job_offer, "owner")
                send_notification_to_hr("Expected DOJ Change", self.job_offer, hr_email)

            except Exception:
                frappe.log_error(frappe.get_traceback(), "Error syncing DOJ with Job Offer")

        # ? SYNC OFFER ACCEPTANCE STATUS IF CHANGED
        if self.has_value_changed("offer_acceptance") and self.job_offer:
            try:
                frappe.db.set_value(
                    "Job Offer",
                    self.job_offer,
                    "status",
                    self.offer_acceptance
                )
            except Exception:
                frappe.log_error(frappe.get_traceback(), "Error syncing offer_acceptance with Job Offer")

        # ? SYNC CONDITION FOR ACCEPTANCE IF CHANGED
        if self.has_value_changed("condition_for_offer_acceptance") and self.job_offer:
            try:
                frappe.db.set_value(
                    "Job Offer",
                    self.job_offer,
                    "custom_condition_for_acceptance",
                    self.condition_for_offer_acceptance
                )
            except Exception:
                frappe.log_error(frappe.get_traceback(), "Error syncing condition_for_offer_acceptance with Job Offer")


# ? SEND NOTIFICATION EMAIL TO HR FROM TEMPLATE
def send_notification_to_hr(notification_name, job_offer_name, recipient):
    try:
        notification = frappe.get_doc("Notification", notification_name)
        context = {
            "doc": {"name": job_offer_name},
            "user": recipient
        }

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
        frappe.log_error(frappe.get_traceback(), f"{notification_name} Notification Error")
