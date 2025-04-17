import frappe

#* API TO SEND EMAIL TO JOB APPLICANT FOR SCREEN TEST
@frappe.whitelist()
def check_test_and_invite(job_applicant):
    try:
        applicant = frappe.get_doc("Job Applicant", job_applicant)
        job_opening = frappe.get_doc("Job Opening", applicant.job_title)

        if not job_opening.custom_applicable_screening_test:
            return { "error":0,"message":"redirect"}

        if not applicant.email_id:
            frappe.throw("No email address found for the applicant.")

        
        subject = "Screen Test Invitation"
        # test_link = get_url(f"/test?applicant={applicant.name}") 
        test_link = "Test Link Url"
        content = f"""
            Dear {applicant.applicant_name},<br><br>
            You are invited to take a screen test for the position of <b>{applicant.job_title}</b>.<br>
            Please click the link below to take the test:<br>
            LINK
            Regards,<br>
            HR Team
        """
    # <a href="{test_link}">{test_link}</a><br><br>
        frappe.sendmail(
            recipients=[applicant.email_id],
            subject=subject,
            message=content
        )
        
        frappe.db.set_value("Job Applicant", job_applicant, "status", "Screening Test Scheduled")
        
        return {"error":0, "message":"invited"}
    except Exception as e:
        frappe.log_error(f"Error in check_test_and_invite", frappe.get_traceback())
        return {"error": 1, "message": str(e)}




import frappe
import json
import traceback

# Generic helper function to send email using Notification Template
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
        # Re-raise the error to be handled by the caller function
        raise

@frappe.whitelist()
def add_to_interview_availability(job_opening, job_applicants, employees):
    try:
        # Ensure job_opening is in string format
        job_opening = str(job_opening) if not isinstance(job_opening, str) else job_opening
        
        # Ensure job_applicants and employees are lists (parse JSON if strings are provided)
        job_applicants = json.loads(job_applicants) if isinstance(job_applicants, str) else job_applicants
        employees = json.loads(employees) if isinstance(employees, str) else employees

        # Get job requisition and company details
        job_requisition = frappe.db.get_value("Job Opening", job_opening, "custom_job_requisition_record")
        company = None
        if job_requisition:
            company = frappe.db.get_value("Job Requisition", job_requisition, "company")

        # Create Interview Availability Form document
        interview_doc = frappe.new_doc("Interview Availability Form")
        interview_doc.job_opening = job_opening
        interview_doc.company = company

        # Set designation, or use default
        interview_doc.for_designation = frappe.db.get_value("Job Opening", job_opening, "designation") or "Interview Panel"

        # ADD JOB APPLICANTS TO CHILD TABLE
        for applicant in job_applicants:
            interview_doc.append("job_applicants", {
                "job_applicant": applicant
            })

        interview_doc.insert(ignore_permissions=True)

        # ? SHARE WITH SELECTED EMPLOYEES
        shared_users = [] 
        for emp in employees:
            user = frappe.db.get_value("Employee", emp, "user_id")
            if user:
                try:
                    # ? SHARE THE DOCUMENT WITH THE USER
                    frappe.share.add(
                        doctype=interview_doc.doctype,
                        name=interview_doc.name,
                        user=user,
                        read=1,
                        write=0,
                        share=0,
                    )
                    shared_users.append(user)
                except Exception as e:
                    frappe.log_error(f"Sharing failed for {emp} ({user}): {str(e)}", "Interview Availability Share Error")

        # ? SEND EMAIL NOTIFICATION AFTER SHARING THE DOCUMENT
        if shared_users:
            send_notification_from_template(
                emails=shared_users,  
                notification_name="Job Applicant Assigning Notification",  
                doc=interview_doc  
            )

        return "Interview Availability created, shared, and email sent successfully."

    except Exception as e:
        frappe.log_error(
            title="Error in Interview Availability",
            message=f"Failed to add to Interview Availability: {str(e)}\n{traceback.format_exc()}",
        )
        return "An error occurred while adding to Interview Availability."
