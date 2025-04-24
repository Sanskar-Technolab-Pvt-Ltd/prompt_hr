# Copyright (c) 2025, Jignasha Chavda and contributors
# For license information, please see license.txt

import frappe
import traceback
from frappe.model.document import Document
from datetime import datetime

class InterviewAvailabilityForm(Document):

    # ? FUNCTION TO UPDATE JOB APPLICANT STATUS + HANDLE HR NOTIFICATIONS
    def before_save(self):
        for applicant in self.job_applicants:

            # ? MAP CHILD STATUS TO JOB APPLICANT STATUS
            status_map = {
                "Open": "Shortlisted by HR",
                "Shortlisted": "Shortlisted by Interviewer"
            }
            new_status = status_map.get(applicant.status, applicant.status)

            # ? GET CURRENT STATUS FROM JOB APPLICANT DOC
            current_status = frappe.db.get_value('Job Applicant', applicant.job_applicant, 'status')

            # ? UPDATE ONLY IF THE STATUS HAS ACTUALLY CHANGED
            if current_status != new_status:
                # UPDATE JOB APPLICANT DOC
                frappe.db.set_value('Job Applicant', applicant.job_applicant, 'status', new_status)

                # SET WHO SHORTLISTED
                if applicant.status == "Shortlisted":
                    applicant.shortlisted_by = frappe.session.user

                # NOTIFY USER IN UI
                # frappe.msgprint(f"Your availability is notified ")

                # NOTIFY HR MANAGERS
                send_notification_to_hr(applicant.job_applicant)

# ? FUNCTION TO NOTIFY HR USERS VIA EMAIL TEMPLATE
def send_notification_to_hr(job_applicant_name):
    hr_users = frappe.db.sql("""
        SELECT DISTINCT hr.parent as email
        FROM `tabHas Role` hr
        INNER JOIN `tabUser` u ON u.name = hr.parent
        WHERE hr.role = 'HR Manager' AND u.enabled = 1
    """, as_dict=1)

    hr_emails = [user.email for user in hr_users]
    
    if hr_emails:
        job_applicant_doc = frappe.get_doc('Job Applicant', job_applicant_name)
        send_notification_from_template(
            emails=hr_emails,
            notification_name="HR Interview Availability Revert Mail",
            doc=job_applicant_doc
        )

# ? FUNCTION TO FETCH LATEST INTERVIEW AVAILABILITY FOR A TIME SLOT
@frappe.whitelist()
def fetch_latest_availability(param_date, param_from_time, param_to_time, designation):
    try:
        from_time = datetime.strptime(param_from_time, "%H:%M:%S").time()
        to_time = datetime.strptime(param_to_time, "%H:%M:%S").time()

        records = frappe.db.get_all(
            "Interview Availability",
            filters={"date": param_date, "designation": designation},
            fields=["name", "from_time", "to_time", "interviewer"],
            order_by="creation DESC"
        )

        latest_record = [
            record["interviewer"]
            for record in records
            if (datetime.strptime(str(record["from_time"]), "%H:%M:%S").time() <= from_time < datetime.strptime(str(record["to_time"]), "%H:%M:%S").time())
            or (datetime.strptime(str(record["from_time"]), "%H:%M:%S").time() < to_time <= datetime.strptime(str(record["to_time"]), "%H:%M:%S").time())
        ]

        return {"status": "Available", "record": latest_record} if latest_record else {"status": "Not Available"}

    except Exception as e:
        frappe.log_error(f"Error in fetch_latest_availability: {str(e)}", "Interview Availability")
        return {"status": "Error", "message": str(e)}

# ? FUNCTION TO SEND EMAIL USING TEMPLATE
def send_notification_from_template(emails, notification_name, doc=None):
    try:
        notification_doc = frappe.get_doc("Notification", notification_name)

        for email in emails:
            context = {"doc": doc or frappe._dict({}), "user": email}
            subject = frappe.render_template(notification_doc.subject, context)
            message = frappe.render_template(notification_doc.message, context)

            # ADD LINK TO JOB APPLICANT FORM
            if doc and doc.doctype and doc.name:
                link = f"{frappe.utils.get_url()}/app/{doc.doctype.replace(' ', '-').lower()}/{doc.name}"
                message += f"<br><br><a href='{link}'>Click here to view the Job Opening</a>"

            frappe.sendmail(recipients=[email], subject=subject, message=message)

        frappe.log_error("Notification Sent", f"Notification '{notification_name}' sent to {len(emails)} employees.")

    except Exception as e:
        frappe.log_error(
            title="Notification Sending Failed",
            message=f"Failed to send '{notification_name}': {str(e)}\n{traceback.format_exc()}",
        )
