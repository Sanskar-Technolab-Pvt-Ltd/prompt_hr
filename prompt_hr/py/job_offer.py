

import frappe
from frappe.utils.print_format import download_pdf
from frappe.utils.file_manager import save_file

@frappe.whitelist()
def release_offer_letter(doctype, docname):
    doc = frappe.get_doc(doctype, docname)
    if doc.job_applicant:
        send_mail_to_job_applicant(doc)

def send_mail_to_job_applicant(doc):
    # FETCH THE CANDIDATE PORTAL BASED ON THE 'JOB_OFFER' FIELD AND 'DOC.NAME'
    candidate_profile = frappe.db.get_value(
        "Candidate Portal",
        {"job_offer": doc.name}, 
        ["applicant_email", "phone_number", "name"],
        as_dict=True
    )
    
    if candidate_profile:
        email = candidate_profile.applicant_email
        phone = candidate_profile.phone_number
        candidate_portal = candidate_profile.name
        print(f"[DEBUG] Email: {email}, Phone: {phone}")
        
        if email and phone:
            fallback_subject = "Update on Your Job Application"
            fallback_message = f"Hello, we've updated your job application. Please check your offer: {doc.name}."
            
            send_notification_email(
                doc_type=doc.doctype,
                doc_name=doc.name,
                recipient=email,
                fallback_subject=fallback_subject,
                fallback_message=fallback_message,
                portal=candidate_portal
            )
        else:
            print(f"[DEBUG] Missing email or phone in Candidate Portal: {candidate_profile}")
    else:
        print(f"[DEBUG] No Candidate Portal found for Job Offer: {doc.name}")

def send_notification_email(doc_type, doc_name, recipient, fallback_subject, fallback_message, portal):
    print(f"[NOTIFICATION EMAIL] Preparing email for {recipient} using DocType: {doc_type}, Name: {doc_name}")
    
    try:
        doc = frappe.get_doc(doc_type, doc_name)
        
        # GET THE FIRST MATCHING NOTIFICATION TEMPLATE FOR THE GIVEN DOCTYPE
        notification_meta = frappe.get_all(
            "Notification",
            filters={"document_type": doc_type, "channel": "Email"},
            limit=1
        )
        
        if not notification_meta:
            raise Exception(f"No Notification template found for {doc_type}")
        
        notification = frappe.get_doc("Notification", notification_meta[0].name)
        
        context = {
            "doc": doc,
            "user": recipient
        }
        
        subject = frappe.render_template(notification.subject, context)
        message = frappe.render_template(notification.message, context)
        
        # ADD THE CANDIDATE PORTAL LINK WITH 'JOB_OFFER' FILTER
        base_url = frappe.utils.get_url()
        record_link = f"{base_url}/app/candidate-portal/{portal}"  
        
        message += f"""
            <hr>
            <p><b>Access Your Candidate Portal:</b> 
            <a href="{record_link}" target="_blank">Click here to view your offer</a></p>
        """
        
        # GENERATE JOB OFFER PRINT FORMAT PDF
        print_format = frappe.db.get_value("Print Format", {"doc_type": doc_type, "disabled": 0}, "name")
        if not print_format:
            print_format = "Standard"  
            
        print(f"[DEBUG] Using print format: {print_format}")
        
        # GET PDF CONTENT
        try:
            pdf_data = frappe.get_print(
                doc_type, 
                doc_name,
                print_format=print_format, 
                as_pdf=True
            )
            
            # CREATE UNIQUE FILENAME
            filename = f"{doc_name.replace(' ', '_')}_offer_letter.pdf"
            
            # SAVE FILE TO FRAPPE
            file_doc = save_file(
                filename,
                pdf_data,
                doc_type,
                doc_name,
                is_private=1
            )
            
            # ADD FILE TO EMAIL ATTACHMENTS
            attachments = [{
                "fname": file_doc.file_name,
                "fcontent": pdf_data
            }]
            
            print(f"[DEBUG] Created attachment: {file_doc.file_name}")
            
        except Exception as pdf_error:
            frappe.log_error(f"Failed to generate PDF: {pdf_error}", "PDF Generation Error")
            attachments = []
            print(f"[ERROR] Failed to generate PDF attachment: {pdf_error}")
    
    except Exception as e:
        frappe.log_error(f"Using fallback message due to: {e}", "Notification Template Error")
        subject = fallback_subject
        message = fallback_message
        attachments = []
    
    frappe.sendmail(
        recipients=[recipient],
        subject=subject,
        message=message,
        attachments=attachments
    )
    print(f"[DEBUG] Email sent to {recipient} with subject: '{subject}'")