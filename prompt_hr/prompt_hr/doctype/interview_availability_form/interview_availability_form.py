# Copyright (c) 2025, Jignasha Chavda and contributors
# For license information, please see license.txt

import frappe
import traceback
from frappe.model.document import Document
from datetime import datetime
from prompt_hr.py.utils import send_notification_email, get_hr_managers_by_company

class InterviewAvailabilityForm(Document):

    # ? FUNCTION TO UPDATE JOB APPLICANT STATUS + HANDLE HR NOTIFICATIONS
    def before_save(self):

        # ? EXIT IF DOCUMENT IS NEW (DO NOT PERFORM ACTIONS YET)
        if self.is_new():
            return

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
                
                # ? UPDATE JOB APPLICANT DOC
                frappe.db.set_value('Job Applicant', applicant.job_applicant, 'status', new_status)

                # ? SET WHO SHORTLISTED
                if applicant.status == "Shortlisted":
                    applicant.shortlisted_by = frappe.session.user

                # ? CLEAR TIME FIELDS IF STATUS CHANGES
                applicant.from_time = None
                applicant.to_time = None

        # ? GET HR EMAILS BASED ON COMPANY
        hr_emails = get_hr_managers_by_company(self.company)
        
        if hr_emails:
            # ? SEND NOTIFICATION EMAIL TO HR MANAGERS
            send_notification_email(
                recipients=hr_emails,
                doctype="Interview Availability Form",
                docname=self.name,
                notification_name="HR Interview Availability Revert Mail"
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


