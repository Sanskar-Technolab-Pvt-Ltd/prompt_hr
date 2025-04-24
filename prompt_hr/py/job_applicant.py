import json
import traceback
import frappe
from prompt_hr.py.utils import send_notification_email



def get_hr_managers_by_company(company):
    return [
        row.email for row in frappe.db.sql("""
            SELECT DISTINCT u.email
            FROM `tabHas Role` hr
            JOIN `tabUser` u ON u.name = hr.parent
            JOIN `tabEmployee` e ON e.user_id = u.name
            WHERE hr.role = 'HR Manager'
              AND u.enabled = 1
              AND e.company = %s
        """, (company,), as_dict=1) if row.email
    ]


def after_insert(doc, method):
    try:

        company = frappe.db.get_value("Job Opening", doc.job_title, "company")

        hr_emails = get_hr_managers_by_company(company)

        if hr_emails:
    
            send_notification_email(
            recipients = hr_emails,
            notification_name="Job Applicant Registration Mail",
            doctype=doc.doctype,
            docname=doc.name,
            button_label="View Details",
            fallback_subject="Notification",
            fallback_message="You have a new update. Please check your portal.",
            extra_context=None
            )

            
         
        else:
            frappe.log_error("No HR Managers Found", f"No HR Managers found for company: {doc.company}")

    except Exception as e:
        frappe.log_error("Error in after_insert", str(e))

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
                    f"<br><br><a href='{link}'>Click here to view the Record</a>"
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
        # ? RE-RAISE THE ERROR TO BE HANDLED BY THE CALLER FUNCTION
        raise


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
        
        send_notification_email(
            recipients = [applicant.email_id],
            notification_name="Screen Test Invitation",
            doctype="Job Applicant",
            docname=applicant.name,
            button_label="View Details",
            fallback_subject="Notification",
            fallback_message="You have a new update. Please check your portal.",
            extra_context=None,
            hash_input_text = applicant.name
        )
       
        
        frappe.db.set_value("Job Applicant", job_applicant, "status", "Screening Test Scheduled")
        
        return {"error":0, "message":"invited"}
    except Exception as e:
        frappe.log_error(f"Error in check_test_and_invite", frappe.get_traceback())
        return {"error": 1, "message": str(e)}



@frappe.whitelist()
def add_to_interview_availability(job_opening, job_applicants, employees):
    try:
        # ? ENSURE JOB_OPENING IS IN STRING FORMAT
        job_opening = str(job_opening) if not isinstance(job_opening, str) else job_opening
        
        # ? ENSURE JOB_APPLICANTS AND EMPLOYEES ARE LISTS (PARSE JSON IF STRINGS ARE PROVIDED)
        job_applicants = json.loads(job_applicants) if isinstance(job_applicants, str) else job_applicants
        employees = json.loads(employees) if isinstance(employees, str) else employees

        # ? GET JOB REQUISITION AND COMPANY DETAILS
        job_requisition = frappe.db.get_value("Job Opening", job_opening, "custom_job_requisition_record")
        company = None
        if job_requisition:
            company = frappe.db.get_value("Job Requisition", job_requisition, "company")

        # ? CREATE INTERVIEW AVAILABILITY FORM DOCUMENT
        interview_doc = frappe.new_doc("Interview Availability Form")
        interview_doc.job_opening = job_opening
        interview_doc.company = company

        # ? SET DESIGNATION, OR USE DEFAULT
        interview_doc.for_designation = frappe.db.get_value("Job Opening", job_opening, "designation") or "Interview Panel"

        # ? ADD JOB APPLICANTS TO CHILD TABLE
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
                notification_name="Send to Interviewer for Availability",  
                doc=interview_doc  
            )

        return "Interview Availability created, shared, and email sent successfully."

    except Exception as e:
        frappe.log_error(
            title="Error in Interview Availability",
            message=f"Failed to add to Interview Availability: {str(e)}\n{traceback.format_exc()}",
        )
        return "An error occurred while adding to Interview Availability."

@frappe.whitelist()
def before_insert(doc, method=None):
    if doc.custom_company:
        # Set the joining document checklist if found
        joining_document_checklist = frappe.get_all(
            "Joining Document Checklist", 
            filters={"company": doc.custom_company}, 
            fields=["name"]
        )
        
        if joining_document_checklist:
            doc.custom_joining_document_checklist = joining_document_checklist[0].name

        # Fetch required documents
        documents_records = frappe.get_all(
            "Required Document Applicant", 
            filters={"company": doc.custom_company}, 
            fields=["name","required_document", "document_collection_stage"]
        )

        if documents_records:
            for record in documents_records:
                doc.append("custom_documents", {
                    "required_document": record.name,
                    "collection_stage": record.document_collection_stage
                })
                frappe.get_doc({
                    "doctype": "Document Collection",
                    "required_document": record.name,
                    "collection_stage": record.document_collection_stage,
                })
                frappe.db.commit()
