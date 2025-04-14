import frappe


# ? AFTER SAVE FUNCTION LINKED IN HOOKS
@frappe.whitelist()
def after_insert(doc, method):
    print(f"[AFTER SAVE] Triggered for {doc.doctype}: {doc.name}")
    
    if doc.job_applicant:
        print(f"[AFTER SAVE] Found Job Applicant: {doc.job_applicant}")
        send_mail_to_job_applicant(doc)
    else:
        print("[AFTER SAVE] No Job Applicant linked to this document.")


def send_mail_to_job_applicant(doc):
    print(f"[SEND MAIL] Fetching contact details for Job Applicant: {doc.job_applicant}")

    # ? FETCH EMAIL AND PHONE NUMBER FROM LINKED JOB APPLICANT
    job_applicant_email = frappe.db.get_value("Job Applicant", doc.job_applicant, "email_id")
    job_applicant_phone_number = frappe.db.get_value("Job Applicant", doc.job_applicant, "phone_number")

    print(f"[SEND MAIL] Email: {job_applicant_email}, Phone: {job_applicant_phone_number}")

    if job_applicant_email and job_applicant_phone_number:
        print("[SEND MAIL] Valid contact info found. Proceeding to send email...")
        fallback_subject = "Update on Your Job Application"
        fallback_message = f"Hello, we’ve updated your job application. Please check your offer: {doc.name}."

        send_notification_email(
            doc_type=doc.doctype,
            doc_name=doc.name,
            recipient=job_applicant_email,
            fallback_subject=fallback_subject,
            fallback_message=fallback_message
        )
    else:
        print("[SEND MAIL] Missing email or phone number. Skipping email sending.")


def send_notification_email(doc_type, doc_name, recipient, fallback_subject, fallback_message):
    print(f"[NOTIFICATION EMAIL] Preparing email for {recipient} using DocType: {doc_type}, Name: {doc_name}")
    
    try:
        doc = frappe.get_doc(doc_type, doc_name)

        # ? FETCH THE FIRST MATCHING NOTIFICATION FOR THE GIVEN DOCTYPE
        notification_meta = frappe.get_all(
            "Notification",
            filters={"document_type": doc_type, "channel": "Email"},
            limit=1
        )

        if not notification_meta:
            raise Exception(f"No Notification template found for {doc_type}")

        print(f"[NOTIFICATION EMAIL] Using Notification Template: {notification_meta[0].name}")
        notification = frappe.get_doc("Notification", notification_meta[0].name)

        context = {
            "doc": doc,
            "user": recipient
        }

        subject = frappe.render_template(notification.subject, context)
        message = frappe.render_template(notification.message, context)

        # ? APPEND CHECKLIST LINK TO EMAIL
        checklist_name = doc_type
        checklist_path = checklist_name.lower().replace(" ", "-")
        base_url = frappe.utils.get_url()
        record_link = f"{base_url}/app/{checklist_path}/{doc.name}"

        message += f"""
            <hr>
            <p><b>Job Offer:</b> 
            <a href="{record_link}" target="_blank">{checklist_name} ({doc.name})</a></p>
        """

        print(f"[NOTIFICATION EMAIL] Email content prepared successfully.")

    except Exception as e:
        frappe.log_error(f"Using fallback message due to: {e}", "Notification Template Error")
        subject = fallback_subject
        message = fallback_message
        print(f"[NOTIFICATION EMAIL] Error encountered. Sending fallback email. Error: {e}")

    frappe.sendmail(
        recipients=[recipient],
        subject=subject,
        message=message
    )

    print(f"✅ Email sent to {recipient} with subject: '{subject}'")
