import json
import traceback
import frappe
from prompt_hr.py.utils import send_notification_email,get_hr_managers_by_company



@frappe.whitelist()
def after_insert(doc, method):
    try:

        hr_emails = get_hr_managers_by_company(doc.custom_company)

        if hr_emails:
    
            send_notification_email(
            recipients = hr_emails,
            notification_name="Job Applicant Registration Mail",
            doctype=doc.doctype,
            docname=doc.name,
            button_label="View Details",    
            )
        else:
            frappe.log_error("No HR Managers Found", f"No HR Managers found for company: {doc.company}")

    except Exception as e:
        frappe.log_error("Error in after_insert", str(e))


# ? API TO SEND EMAIL TO JOB APPLICANT FOR SCREEN TEST
@frappe.whitelist()
def check_test_and_invite(job_applicant):
    try:
        # ? GET BASIC INFO OF THE APPLICANT
        applicant = frappe.db.get_value("Job Applicant", job_applicant, ["email_id", "job_title",], as_dict=True)
        interview_round = frappe.db.get_value("Job Opening", applicant.job_title, "custom_applicable_screening_test")
        if not applicant:
            return {"error": 1, "message": "Job Applicant not found."}

        if not interview_round:
            return {"error": 0, "message": "redirect","applicant": applicant}

        if not applicant.email_id:
            frappe.throw("No email address found for the applicant.")

        # ? SEND SCREENING TEST INVITATION
        send_notification_email(
            recipients=[applicant.email_id],
            notification_name="Screen Test Invitation",
            doctype="Job Applicant",
            docname=job_applicant,
            button_label="View Details",
            button_link=f"http://192.168.2.111:8007/lms/courses/{interview_round}/learn/1-1",
            hash_input_text=job_applicant
        )

        # ? UPDATE STATUS TO INDICATE SCREENING TEST IS SCHEDULED
        frappe.db.set_value("Job Applicant", job_applicant, "status", "Screening Test Scheduled")

        return {"error": 0, "message": "invited"}

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
        frappe.db.commit()

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
            send_notification_email(
                recipients=shared_users,  
                notification_name="Send to Interviewer for Availability",  
                doctype=interview_doc.doctype,
                docname=interview_doc.name,
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
        # ? SET THE JOINING DOCUMENT CHECKLIST IF FOUND
        joining_document_checklist = frappe.get_all(
            "Joining Document Checklist", 
            filters={"company": doc.custom_company}, 
            fields=["name"]
        )
        
        if joining_document_checklist:
            doc.custom_joining_document_checklist = joining_document_checklist[0].name

        # ? FETCH REQUIRED DOCUMENTS
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
                frappe.db.commit()
