import frappe
from frappe.utils.print_format import download_pdf
from frappe.utils.file_manager import save_file
from prompt_hr.py.utils import create_hash,send_notification_email, get_email_ids_for_roles, get_roles_from_hr_settings_by_module


# ? SYNC CANDIDATE PORTAL ON JOB OFFER INSERT
def after_insert(doc, method):
    sync_candidate_portal_from_job_offer(doc)

def on_cancel(doc, method=None):
    if doc.workflow_state:
        doc.workflow_state = "Cancelled"

def on_update(doc, method=None):
    if doc.workflow_state and doc.workflow_state == "Pending":
        # Fetch HR roles from HR Settings
        try:
            hr_roles = get_roles_from_hr_settings_by_module("custom_hr_roles_for_recruitment")
            recipients = get_email_ids_for_roles(hr_roles) if hr_roles else []
        except:
            recipients = []

        # Send Notification Email
        try:
            if recipients:
                send_notification_email(
                    notification_name="Job Offer Update Notification",
                    recipients=recipients,
                    doctype="Job Offer",
                    docname=doc.name,
                    button_label="View Job Offer",
                    send_link=True,
                    send_header_greeting=False,
                )
        except Exception as e:
            frappe.log_error(message=str(e), title="Job Offer Update Notification Error")


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


@frappe.whitelist()
def sync_candidate_portal_from_job_offer(job_offer):
    """
    SYNC CANDIDATE PORTAL ENTRY BASED ON JOB OFFER
    This method is triggered from Job Offer submission/update.
    It creates or updates Candidate Portal entry and enqueues PDF generation.
    """

    try:
        # ! CONVERT TO DICT IF JOB OFFER NAME IS PASSED
        if isinstance(job_offer, str):
            job_offer_fields = frappe.db.get_value(
                "Job Offer",
                job_offer,
                ["name", "job_applicant", "offer_date", "custom_expected_date_of_joining", "status","designation","custom_department","custom_location","custom_business_unit","custom_employment_type","custom_employee","custom_employee_name","custom_phone_no","custom_monthly_base_salary"],
                as_dict=True
            )
            if not job_offer_fields:
                frappe.throw("Job Offer not found.")
            job_offer = job_offer_fields
        
        print("\n\n>>> Job Offer object:", job_offer)

        # ! CHECK JOB APPLICANT EXISTS
        if not job_offer.get("job_applicant"):
            frappe.throw("Job Applicant not linked in Job Offer.")

        # ! GET APPLICANT EMAIL
        email = frappe.db.get_value("Job Applicant", job_offer.get("job_applicant"), "email_id")
        if not email:
            frappe.throw("Email ID not found for Job Applicant.")

        # ! CREATE OR UPDATE CANDIDATE PORTAL
        portal_name = frappe.db.get_value("Candidate Portal", {"applicant_email": job_offer.get("job_applicant")}, "name")
        portal = frappe.get_doc("Candidate Portal", portal_name) if portal_name else frappe.new_doc("Candidate Portal")

        portal.update({
            "applicant_email": job_offer.get("job_applicant"),
            "job_offer": job_offer.get("name"),
            "offer_date": job_offer.get("offer_date"),
            "expected_date_of_joining": job_offer.get("custom_expected_date_of_joining"),
            "offer_acceptance": job_offer.get("status"),
            "department":job_offer.get("custom_department"),
            "location":job_offer.get("custom_location"),
            "business_unit":job_offer.get("custom_business_unit"),
            "employment_type":job_offer.get("custom_employment_type"),
            "employee":job_offer.get("custom_employee"),
            "employee_name":job_offer.get("custom_employee_name"),
            "phone_no":job_offer.get("custom_phone_no"),
            "monthly_base_salary":job_offer.get("custom_monthly_base_salary")
        })

        print(">>> Candidate Portal prepared:", portal.as_dict())

        # ! SAVE BEFORE GENERATING PDF
        if portal_name:
            portal.save(ignore_permissions=True)
        else:
            portal.insert(ignore_permissions=True)

        frappe.db.commit()

        # ! ENQUEUE BACKGROUND PDF ATTACHMENT
        frappe.enqueue(
            method="prompt_hr.py.job_offer.generate_offer_letter_pdf",
            job_offer_name=job_offer.get("name"),
            portal_name=portal.name,
            queue='default',
            now=False,
        )

        frappe.msgprint("Candidate Portal updated from Job Offer.")
        return portal.name

    except Exception as e:
        frappe.log_error(frappe.get_traceback(), "❌ sync_candidate_portal_from_job_offer Error")
        frappe.throw("Something went wrong while syncing Candidate Portal.")

def generate_offer_letter_pdf(job_offer_name, portal_name):
    """
    BACKGROUND TASK: Generate PDF for Job Offer and attach to Candidate Portal
    Called via frappe.enqueue in sync_candidate_portal_from_job_offer
    """
    try:
        print(f">>> [PDF] Generating for Job Offer: {job_offer_name}, Portal: {portal_name}")

        # ! LOAD DOCS
        job_offer = frappe.get_doc("Job Offer", job_offer_name)
        portal = frappe.get_doc("Candidate Portal", portal_name)

        # ! GET PRINT FORMAT
        print_format = frappe.db.get_value(
            "Print Format", {"doc_type": "Job Offer", "disabled": 0}, "name"
        )

        print(f">>> [PDF] Using print format: {print_format}")

        # ! GENERATE PDF
        pdf_file = frappe.attach_print(
            "Job Offer",
            job_offer.name,
            print_format=print_format,
            print_letterhead=True,
        )

        # ! SAVE FILE IN SYSTEM
        file_doc = frappe.get_doc({
            "doctype": "File",
            "file_name": f"Job Offer - {job_offer.name}.pdf",
            "content": pdf_file.get("fcontent"),
            "is_private": 1,
            "attached_to_doctype": "Job Offer",
            "attached_to_name": job_offer.name,
        }).insert()

        # ! SET OFFER LETTER LINK
        from frappe.utils import get_url
        portal.offer_letter = get_url(file_doc.file_url)
        portal.save(ignore_permissions=True)
        frappe.db.commit()

        print(f">>> [PDF] PDF attached and portal updated: {portal.offer_letter}")

    except Exception as e:
        frappe.log_error(frappe.get_traceback(), "generate_offer_letter_pdf Error")
        print(">>> [PDF] Error occurred during PDF generation. Check error logs.")


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
                    {"applicant_email": job_offer_doc.job_applicant, "job_offer": job_offer_doc.name}, 
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
    try:
        # ? FETCH THE DOCUMENT
        doc = frappe.get_doc(doctype, docname)

        if not doc.job_applicant:
            return {
                "status": "error",
                "message": "No Job Applicant linked with this Job Offer."
            }

        # ? ENSURE CANDIDATE PORTAL EXISTS
        portal_name = ensure_candidate_portal_exists(doc)
        if not portal_name:
            return {
                "status": "error",
                "message": "Could not create or find Candidate Portal for this Job Offer."
            }

        # ? SEND THE EMAIL
        send_mail_to_job_applicant(
            doc,
            is_resend=frappe.parse_json(is_resend),
            notification_name=notification_name,
        )

        return {
            "status": "success",
            "message": "Offer Letter successfully sent to the candidate."
        }

    except frappe.DoesNotExistError:
        frappe.log_error(frappe.get_traceback(), "Job Offer Document Not Found")
        return {
            "status": "error",
            "message": "The specified Job Offer document does not exist."
        }

    except Exception:
        frappe.log_error(frappe.get_traceback(), "Error in release_offer_letter")
        return {
            "status": "error",
            "message": "Something went wrong while releasing the offer letter."
        }


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