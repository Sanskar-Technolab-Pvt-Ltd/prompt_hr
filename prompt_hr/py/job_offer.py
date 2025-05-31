import frappe
from frappe.utils.print_format import download_pdf
from frappe.utils.file_manager import save_file
from prompt_hr.py.utils import create_hash,send_notification_email


# ? SYNC CANDIDATE PORTAL ON JOB OFFER INSERT
def after_insert(doc, method):
    sync_candidate_portal_from_job_offer(doc)


# ? SYNC CANDIDATE RESPONSE FIELDS FROM PORTAL TO JOB OFFER
@frappe.whitelist()
def accept_changes(
    job_offer,
    custom_candidate_date_of_joining=None,
    custom_candidate_offer_acceptance=None,
    custom_candidate_condition_for_offer_acceptance=None,
):
    try:
        # ? GET CANDIDATE PORTAL LINKED TO JOB OFFER
        portal = frappe.db.get_value(
            "Candidate Portal", {"job_offer": job_offer}, "name"
        )
        if not portal:
            frappe.throw("Candidate Portal not found for this Job Offer.")

        updates = {}

        # ? SYNC EXPECTED JOINING DATE
        if custom_candidate_date_of_joining:
            updates["expected_date_of_joining"] = custom_candidate_date_of_joining
            frappe.db.set_value(
                "Job Offer",
                job_offer,
                "custom_expected_date_of_joining",
                custom_candidate_date_of_joining,
            )

        # ? SYNC OFFER ACCEPTANCE
        if custom_candidate_offer_acceptance:
            updates["offer_acceptance"] = custom_candidate_offer_acceptance
            frappe.db.set_value(
                "Job Offer", job_offer, "status", custom_candidate_offer_acceptance
            )

        # ? SYNC CONDITIONS
        if custom_candidate_condition_for_offer_acceptance:
            updates["condition_for_offer_acceptance"] = (
                custom_candidate_condition_for_offer_acceptance
            )
            frappe.db.set_value(
                "Job Offer",
                job_offer,
                "custom_condition_for_acceptance",
                custom_candidate_condition_for_offer_acceptance,
            )

        if updates:
            frappe.db.set_value("Candidate Portal", portal, updates)

        return True

    except Exception as e:
        frappe.log_error(f"Failed to accept changes for Job Offer {job_offer}: {e}")
        frappe.throw("Something went wrong while accepting the offer changes.")


# ? CREATE OR UPDATE CANDIDATE PORTAL FROM JOB OFFER
@frappe.whitelist()
def sync_candidate_portal_from_job_offer(job_offer):
    try:
        # ? CONVERT TO DOC IF NAME PASSED
        if isinstance(job_offer, str):
            job_offer = frappe.get_doc("Job Offer", job_offer)

        if not job_offer.job_applicant:
            frappe.throw("Job Applicant not linked in Job Offer.")

        # ? GET JOB APPLICANT EMAIL
        email = frappe.db.get_value(
            "Job Applicant", job_offer.job_applicant, "email_id"
        )
        if not email:
            frappe.throw("Email ID not found for Job Applicant.")

        # ? CREATE OR UPDATE CANDIDATE PORTAL
        portal_name = frappe.db.exists("Candidate Portal", {"applicant_email": email})
        portal = (
            frappe.get_doc("Candidate Portal", portal_name)
            if portal_name
            else frappe.new_doc("Candidate Portal")
        )

        portal.update(
            {
                "applicant_email": email,
                "job_offer": job_offer.name,
                "offer_date": job_offer.offer_date,
                "expected_date_of_joining": job_offer.custom_expected_date_of_joining,
                "offer_acceptance": job_offer.status,
            }
        )

        # ? ATTACH OFFER LETTER PDF
        try:
            print_format = frappe.db.get_value(
                "Print Format", {"doc_type": "Job Offer", "disabled": 0}, "name"
            )
            pdf_file = frappe.attach_print(
                "Job Offer",
                job_offer.name,
                print_format=print_format,
                print_letterhead=True,
            )
            file_doc = frappe.get_doc(
                {
                    "doctype": "File",
                    "file_name": f"Job Offer - {job_offer.name}.pdf",
                    "content": pdf_file.get("fcontent"),
                    "is_private": 1,
                    "attached_to_doctype": "Job Offer",
                    "attached_to_name": job_offer.name,
                }
            ).insert()
            portal.offer_letter = f"http://192.168.2.111:8007{file_doc.file_url}"
        except Exception:
            frappe.log_error(frappe.get_traceback(), "Offer Letter PDF Error")

        (
            portal.save(ignore_permissions=True)
            if portal_name
            else portal.insert(ignore_permissions=True)
        )
        frappe.db.commit()
        frappe.msgprint("Candidate Portal updated from Job Offer.")
        
        return portal.name

    except Exception as e:
        frappe.log_error(f"Failed to sync Candidate Portal: {e}")
        frappe.throw("Something went wrong while syncing Candidate Portal.")


# ? ENSURE CANDIDATE PORTAL EXISTS FOR JOB OFFER
def ensure_candidate_portal_exists(job_offer_doc):
    """
    Check if candidate portal exists for the job offer, create if it doesn't
    Returns the portal name
    """
    try:
        # Check if portal already exists
        if job_offer_doc.job_applicant:
            email = frappe.db.get_value(
                "Job Applicant", job_offer_doc.job_applicant, "email_id"
            )
            if email:
                portal_name = frappe.db.get_value(
                    "Candidate Portal", 
                    {"applicant_email": email, "job_offer": job_offer_doc.name}, 
                    "name"
                )
                
                if portal_name:
                    return portal_name
                else:
                    # Portal doesn't exist, create it
                    frappe.logger().info(f"Creating candidate portal for Job Offer: {job_offer_doc.name}")
                    return sync_candidate_portal_from_job_offer(job_offer_doc)
    except Exception as e:
        frappe.log_error(f"Error ensuring candidate portal exists: {e}")
        
    return None


# ? RELEASE JOB OFFER TO CANDIDATE
@frappe.whitelist()
def release_offer_letter(doctype, docname, is_resend=False, notification_name=None):
    doc = frappe.get_doc(doctype, docname)

    if doc.job_applicant:
        # Ensure candidate portal exists before sending
        portal_name = ensure_candidate_portal_exists(doc)
        if not portal_name:
            frappe.throw("Could not create or find Candidate Portal for this Job Offer.")
            
        send_mail_to_job_applicant(
            doc,
            is_resend=frappe.parse_json(is_resend),
            notification_name=notification_name,
        )


# ? SEND JOB OFFER EMAIL TO CANDIDATE
def send_mail_to_job_applicant(doc, is_resend=False, notification_name=None):
    try:
        # Ensure candidate portal exists before trying to send email
        portal_name = ensure_candidate_portal_exists(doc)
        if not portal_name:
            frappe.log_error("Candidate Portal could not be created", "Portal Creation Error")
            return

        candidate = frappe.db.get_value(
            "Candidate Portal",
            {"job_offer": doc.name},
            ["applicant_email", "phone_number", "name"],
            as_dict=True,
        )

        if not candidate or not candidate.applicant_email:
            frappe.log_error(
                f"Invalid candidate portal data: {candidate}", "Candidate Portal Error"
            )
            return

        attachments = get_offer_letter_attachment(doc)
        if is_resend:
            notification_name = notification_name or "Resend Job Offer"

        letter_head = frappe.db.get_value("Letter Head",{"is_default": 1},"name")
        print_format = frappe.db.get_value("Print Format", {"disabled": 0, "doc_type": doc.doctype}, "name")

        send_notification_email(
            recipients=[candidate.applicant_email],
            notification_name=notification_name,
            doctype="Job Offer",
            docname=doc.name,
            hash_input_text=candidate.name,
            button_link=f"/login?redirect-to=/candidate-portal/new#login",
            send_attach=True,
            letterhead=letter_head,
            print_format=print_format
        )

    except Exception:
        frappe.log_error(frappe.get_traceback(), "Error in send_mail_to_job_applicant")


# ? RETURN OFFER LETTER PDF AS ATTACHMENT
def get_offer_letter_attachment(doc):
    try:
        print_format = (
            frappe.db.get_value(
                "Print Format", {"doc_type": doc.doctype, "disabled": 0}, "name"
            )
            or "Job Offer"
        )
        pdf_data = frappe.get_print(
            doc.doctype, doc.name, print_format=print_format, as_pdf=True
        )
        filename = f"{doc.name.replace(' ', '_')}_offer_letter.pdf"
        save_file(filename, pdf_data, doc.doctype, doc.name, is_private=1)
        return [{"fname": filename, "fcontent": pdf_data}]
    except Exception:
        frappe.log_error(frappe.get_traceback(), "PDF Generation Error")
        return []


@frappe.whitelist()
def send_LOI_letter(name):
    doc = frappe.get_doc("Job Offer", name)
    
    # Ensure candidate portal exists before sending LOI
    portal_name = ensure_candidate_portal_exists(doc)
    if not portal_name:
        frappe.throw("Could not create or find Candidate Portal for this Job Offer.")
    
    notification = frappe.get_doc("Notification", "LOI Letter Notification")
    subject = frappe.render_template(notification.subject, {"doc": doc})
    message = frappe.render_template(notification.message, {"doc": doc})
    email = doc.applicant_email if doc.applicant_email else None
    attachment = None
    
    if notification.attach_print and notification.print_format:
        pdf_content = frappe.get_print(
            "Job Offer", 
            doc.name, 
            print_format=notification.print_format, 
            as_pdf=True
        )
        
        attachment = {
            "fname": f"{notification.print_format}.pdf",
            "fcontent": pdf_content
        }

    if email:
        frappe.sendmail(
            recipients=email,
            subject=subject,
            content=message,
            attachments=[attachment] if attachment else None
        )
    else:
        frappe.throw("No Email found for Employee")
    return "LOI Letter sent Successfully"