

import frappe
from frappe.utils.print_format import download_pdf
from frappe.utils.file_manager import save_file


# ! prompt_hr.py.job_offer.release_offer_letter
# ? RELEASE OFFER LETTER AND NOTIFY CANDIDATE
@frappe.whitelist()
def release_offer_letter(doctype, docname, is_resend=False):
    doc = frappe.get_doc(doctype, docname)

    # ? PROCEED ONLY IF A JOB APPLICANT IS LINKED
    if doc.job_applicant:
        send_mail_to_job_applicant(doc, is_resend=frappe.parse_json(is_resend))


# ? SEND NOTIFICATION EMAIL TO JOB APPLICANT
def send_mail_to_job_applicant(doc, is_resend=False):
    try:
        # ? FETCH CANDIDATE PORTAL RECORD LINKED TO THIS JOB OFFER
        candidate = frappe.db.get_value(
            "Candidate Portal",
            {"job_offer": doc.name},
            ["applicant_email", "phone_number", "name"],
            as_dict=True,
        )

        # ? VALIDATE CONTACT DETAILS
        if not candidate or not (candidate.applicant_email and candidate.phone_number):
            frappe.log_error(f"Invalid candidate portal data: {candidate}", "Candidate Portal Error")
            return

        # ? PREPARE EMAIL CONTEXT
        email = candidate.applicant_email
        portal = candidate.name
        attachments = get_offer_letter_attachment(doc)

        # ? HANDLE RESEND SPECIFIC NOTIFICATION
        if is_resend:
            send_specific_notification("Resend Job Offer", doc, email, attachments)
        else:
            send_notification_email(
                doc_type=doc.doctype,
                doc_name=doc.name,
                recipient=email,
                fallback_subject="Update on Your Job Application",
                fallback_message=f"Hello, we've updated your job application. Please check your offer: {doc.name}",
                portal=portal,
                attachments=attachments,
            )

    except Exception:
        frappe.log_error(frappe.get_traceback(), "Error in send_mail_to_job_applicant")


# ? GET JOB OFFER PDF AS ATTACHMENT
def get_offer_letter_attachment(doc):
    try:
        print_format = (
            frappe.db.get_value("Print Format", {"doc_type": doc.doctype, "disabled": 0}, "name")
            or "Job Offer"
        )
        pdf_data = frappe.get_print(doc.doctype, doc.name, print_format=print_format, as_pdf=True)
        filename = f"{doc.name.replace(' ', '_')}_offer_letter.pdf"
        save_file(filename, pdf_data, doc.doctype, doc.name, is_private=1)
        return [{"fname": filename, "fcontent": pdf_data}]
    except Exception:
        frappe.log_error(frappe.get_traceback(), "PDF Generation Error")
        return []


# ? SEND SYSTEM NOTIFICATION EMAIL TO CANDIDATE
def send_notification_email(
    doc_type, doc_name, recipient, fallback_subject, fallback_message, portal, attachments
):
    try:
        doc = frappe.get_doc(doc_type, doc_name)

        # ? FETCH FIRST MATCHING NOTIFICATION TEMPLATE
        notification_meta = frappe.get_all(
            "Notification", filters={"document_type": doc_type, "channel": "Email"}, limit=1
        )
        if not notification_meta:
            raise Exception(f"No Notification template found for {doc_type}")

        notification = frappe.get_doc("Notification", notification_meta[0].name)
        context = {"doc": doc, "user": recipient}

        subject = frappe.render_template(notification.subject, context)
        message = frappe.render_template(notification.message, context)

        # ? ADD CANDIDATE PORTAL LINK TO MESSAGE
        base_url = frappe.utils.get_url()
        message += f"""
            <hr>
            <p><b>Access Your Candidate Portal:</b> 
            <a href="{base_url}/app/candidate-portal/{portal}" target="_blank">Click here to view your offer</a></p>
        """

    except Exception:
        frappe.log_error(frappe.get_traceback(), "Notification Template Error")
        subject = fallback_subject
        message = fallback_message

    # ? SEND FINAL EMAIL
    try:
        frappe.sendmail(
            recipients=[recipient],
            subject=subject,
            message=message,
            attachments=attachments,
        )
    except Exception:
        frappe.log_error(frappe.get_traceback(), "Email Sending Error")


# ? SEND SPECIFIC HARDCODED NOTIFICATION (E.G. RESEND)
def send_specific_notification(notification_name, doc, recipient, attachments):
    try:
        notification = frappe.get_doc("Notification", notification_name)
        context = {"doc": doc, "user": recipient}
        subject = frappe.render_template(notification.subject, context)
        message = frappe.render_template(notification.message, context)

        frappe.sendmail(
            recipients=[recipient],
            subject=subject,
            message=message,
            attachments=attachments,
        )
    except Exception:
        frappe.log_error(frappe.get_traceback(), f"{notification_name} Notification Error")
