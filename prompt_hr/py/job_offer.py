import frappe
from frappe.utils.print_format import download_pdf
from frappe.utils.file_manager import save_file
from prompt_hr.py.utils import create_hash


def validate(doc, method):
    sync_candidate_portal_from_job_offer(doc)


# ? FUNCTION TO CREATE OR UPDATE CANDIDATE PORTAL FROM JOB OFFER
def sync_candidate_portal_from_job_offer(job_offer):
    try:
      
        if not job_offer.job_applicant:
            frappe.throw("Job Applicant not linked in Job Offer.")

        # ? GET EMAIL ID FROM JOB APPLICANT
        applicant_email = frappe.db.get_value("Job Applicant", job_offer.job_applicant, "email_id")
        if not applicant_email:
            frappe.throw("Email ID not found for Job Applicant.")

        # ? CHECK FOR EXISTING CANDIDATE PORTAL
        portal_name = frappe.db.exists("Candidate Portal", {"applicant_email": applicant_email})

        if portal_name:
            portal = frappe.get_doc("Candidate Portal", portal_name)
        else:
            portal = frappe.new_doc("Candidate Portal")
            portal.applicant_email = applicant_email

        # ? SET FIELDS FROM JOB OFFER → CANDIDATE PORTAL
        portal.job_offer = job_offer.name
        portal.offer_date = job_offer.offer_date
        portal.expected_date_of_joining = job_offer.custom_expected_date_of_joining
        portal.offer_acceptance = job_offer.status

        print_format = frappe.db.get_value("Print Format", {"doc_type": "Job Offer", "disabled": 0}, "name")

        # ? ATTACH PRINT FORMAT AS OFFER LETTER PDF
        try:
            # ? Generate PDF and attach as a file
            pdf_file = frappe.attach_print(
                doctype="Job Offer",
                name=job_offer.name,
                print_format=print_format,  # e.g., "Standard" or your custom format
                print_letterhead=True
            )

            print(f"PDF generated: {pdf_file}")

            # ? CREATE A FILE DOCUMENT FROM THE PDF OBJECT
            file_doc = frappe.get_doc({
                "doctype": "File",
                "file_name": f"Job Offer - {job_offer.name}.pdf",
                "content": pdf_file.get("fcontent"),
                "is_private": 1,
                "attached_to_doctype": "Job Offer",
                "attached_to_name": job_offer.name
            }).insert()

            # ? STORE FILE URL IN CANDIDATE PORTAL
            portal.offer_letter= f'http://192.168.2.111:8007{file_doc.file_url}'


            print(f"PDF uploaded: {file_doc.file_url}")

        except Exception as e:
            frappe.log_error(title="Offer Letter PDF Error", message=frappe.get_traceback())


        # ? SAVE OR INSERT
        if portal_name:
            portal.save(ignore_permissions=True)
        else:
            portal.insert(ignore_permissions=True)

        frappe.db.commit()
        frappe.msgprint("Candidate Portal updated from Job Offer.")

    except Exception as e:
        frappe.log_error(f"Failed to sync Candidate Portal: {e}")
        frappe.throw("Something went wrong while syncing Candidate Portal. Please check the logs.")


# ! prompt_hr.py.job_offer.release_offer_letter
# ? RELEASE OFFER LETTER AND NOTIFY CANDIDATE
@frappe.whitelist()
def release_offer_letter(doctype, docname, is_resend=False, notification_name=None):
    doc = frappe.get_doc(doctype, docname)

    # ? PROCEED ONLY IF A JOB APPLICANT IS LINKED
    if doc.job_applicant:
        send_mail_to_job_applicant(doc, is_resend=frappe.parse_json(is_resend), notification_name=notification_name)


# ? SEND NOTIFICATION EMAIL TO JOB APPLICANT
def send_mail_to_job_applicant(doc, is_resend=False, notification_name=None):
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

        # ? DETERMINE WHICH NOTIFICATION TO SEND
        if is_resend:
            notification_name = notification_name or "Resend Job Offer"
        
        # ? SEND EMAIL WITH APPROPRIATE NOTIFICATION
        send_notification_with_portal_link(
            notification_name=notification_name,
            doc=doc,
            recipient=email,
            portal=portal,
            attachments=attachments,
            fallback_subject="Update on Your Job Application",
            fallback_message=f"Hello, we've updated your job application. Please check your offer: {doc.name}"
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


# ? UNIFIED NOTIFICATION HANDLER WITH PORTAL LINK
def send_notification_with_portal_link(
    notification_name, doc, recipient, portal, attachments, fallback_subject=None, fallback_message=None
):
    try:
        frappe.logger().debug(f"Sending notification: {notification_name} for {doc.name} to {recipient}")
        
        # ? If notification name is provided, use that specific template
        if notification_name:
            notification = frappe.get_doc("Notification", notification_name)
        else:
            # ? Otherwise fetch based on document type
            notification_meta = frappe.get_all(
                "Notification", 
                filters={"document_type": doc.doctype, "channel": "Email"}, 
                limit=1
            )
            if not notification_meta:
                raise Exception(f"No Notification template found for {doc.doctype}")
            notification = frappe.get_doc("Notification", notification_meta[0].name)
        
        # ? Prepare context and render templates
        context = {"doc": doc, "user": recipient}
        subject = frappe.render_template(notification.subject, context)
        message = frappe.render_template(notification.message, context)
        
        # ? GENERATE HASH FOR PORTAL ACCESS
        hash_value = create_hash(portal)
        frappe.logger().debug(f"Generated hash for {doc.name}: {hash_value}")
        
        # ? ADD CANDIDATE PORTAL LINK TO MESSAGE
        base_url = frappe.utils.get_url()
        message += f"""
            <hr>
            <p><b>Access Your Candidate Portal:</b> 
            <div>Password: {hash_value}</div>
            <a href="{base_url}/app/candidate-portal/{portal}" target="_blank">Click here to view your offer</a></p>
        """

    except Exception as e:
        frappe.log_error(frappe.get_traceback(), f"Notification Template Error: {str(e)}")
        if fallback_subject and fallback_message:
            subject = fallback_subject
            message = fallback_message
        else:
            raise

    # ? SEND FINAL EMAIL
    try:
        frappe.sendmail(
            recipients=[recipient],
            subject=subject,
            message=message,
            attachments=attachments,
        )
        frappe.logger().debug(f"Email sent successfully to {recipient}")
    except Exception as e:
        frappe.log_error(frappe.get_traceback(), f"Email Sending Error: {str(e)}")