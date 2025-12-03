import frappe
from frappe.utils.print_format import download_pdf
from frappe.utils.file_manager import save_file
from prompt_hr.py.utils import create_hash,send_notification_email, get_email_ids_for_roles, get_roles_from_hr_settings_by_module
from hrms.payroll.doctype.salary_slip.salary_slip import SalarySlip, _safe_eval, get_salary_component_data
from frappe.utils import (
    ceil, floor, flt, cint, get_first_day,
    get_last_day, getdate, rounded
)
from datetime import date
from frappe.utils.pdf import get_pdf
from frappe.www.printview import get_print_format
from frappe import _
import json


# ? SYNC CANDIDATE PORTAL ON JOB OFFER INSERT
def after_insert(doc, method):
    sync_candidate_portal_from_job_offer(doc)


def before_save(doc, method):
    fields_to_track = [
        "custom_salary_structure",
        "custom_monthly_base_salary",
        "custom_pf_consent",
        "custom_esi_consent",
        "custom_nps_consent",
        "custom_lwf_consent",
        "custom_meal_card_consent",
        "custom_attire_card_consent",
        "custom_fuel_card_consent",
        "custom_telephone_reimbursement_applicable",
        "custom_meal_card_amount",
        "custom_fuel_card_amount",
        "custom_attire_card_amount",
        "custom_mobile_internent_card_amount",
        "custom_total_arrear_payable",
        "custom_annual_loyalty_bonus",
        "custom_annual_performance_incentive",
        "custom_variable",
        "custom_manual_basic",
    ]

    if did_change(doc, fields_to_track):
        set_salary_components_with_amount(doc)

    calculate_gross_pay_and_deductions(doc)

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


# ? Create an Employee Letter Approval record.
@frappe.whitelist()
def create_employee_letter_approval(letter="Offer Letter - PROMPT",
                                    released_on_job_applicant_email=None, record=None, record_link=None,
                                    released_by_emp_code_and_name=None, job_applicant_name=None):
    print("record_name", record_link)
    # Build base fields
    doc_fields = {
        "doctype": "Employee Letter Approval",
        "letter": letter,
        "job_applicant_email": released_on_job_applicant_email,
        "job_applicant_name": job_applicant_name,
        "released_on_job_applicant_email": 1 if bool else 0,
        "released_by_emp_code_and_name": released_by_emp_code_and_name ,
        "record": record,
        "record_link": record_link,
    }
 
    # Create record
    doc = frappe.get_doc(doc_fields)
    doc.insert(ignore_permissions=True)

    
    # try:
    #     print_format_name = "Offer Letter - PROMPT"
    #     pdf_filename = "Offer Letter - PROMPT.pdf"

    #     # Generate PDF using print format
    #     pdf_content = frappe.get_print(
    #         "Employee Letter Approval",
    #         doc.name,
    #         print_format=print_format_name,
    #         as_pdf=True
    #     )

    #     # Save file and attach
    #     file_doc = save_file(
    #         pdf_filename,
    #         pdf_content,
    #         doc.doctype,
    #         doc.name,
    #         is_private=False
    #     )

    #     if file_doc:
    #         doc.db_set("attachment", file_doc.file_url)

    # except Exception:
    #     # Fallback: HTML to PDF if print format fails
    #     try:
    #         html = frappe.render_template(
    #             "prompt_hr/templates/includes/job_offer.html",
    #             {"employee": doc.name, "letter": doc.letter}
    #         )

    #         pdf = get_pdf(html)

    #         file_doc = save_file(
    #             pdf_filename,
    #             pdf,
    #             doc.doctype,
    #             doc.name,
    #             is_private=False
    #         )

    #         if file_doc:
    #             doc.db_set("attachment", file_doc.file_url)

    #     except Exception:
    #         frappe.log_error(
    #             frappe.get_traceback(),
    #             "create_employee_letter_approval: PDF generation failed"
    #         )

    return {
        "status": "success",
        "message": _("Letter recorded: {0}").format(doc.name)
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


# @frappe.whitelist()
# def send_LOI_letter(name):
#     doc = frappe.get_doc("Job Offer", name)
    
#     # Ensure candidate portal exists before sending LOI
#     portal_name = ensure_candidate_portal_exists(doc)
#     if not portal_name:
#         frappe.throw("Could not create or find Candidate Portal for this Job Offer.")
    
#     notification = frappe.get_doc("Notification", "LOI Letter Notification")
#     subject = frappe.render_template(notification.subject, {"doc": doc})
#     message = frappe.render_template(notification.message, {"doc": doc})
#     email = doc.applicant_email if doc.applicant_email else None
#     attachment = None
    
#     if notification.attach_print and notification.print_format:
#         pdf_content = frappe.get_print(
#             "Job Offer", 
#             doc.name, 
#             print_format=notification.print_format, 
#             as_pdf=True
#         )
        
#         attachment = {
#             "fname": f"{notification.print_format}.pdf",
#             "fcontent": pdf_content
#         }

#     if email:
#         frappe.sendmail(
#             recipients=email,
#             subject=subject,
#             content=message,
#             attachments=[attachment] if attachment else None
#         )
#     else:
#         frappe.throw("No Email found for Employee")
#     return "LOI Letter sent Successfully"


@frappe.whitelist()
def send_LOI_letter(name, to_users=None, cc_users=None):
    doc = frappe.get_doc("Job Offer", name)

    # Convert JSON string to list if needed
    if isinstance(to_users, str):
        to_users = json.loads(to_users)
    if isinstance(cc_users, str):
        cc_users = json.loads(cc_users)

    # Always ensure lists
    to_users = to_users or []
    cc_users = cc_users or []

    # Ensure candidate portal exists
    portal_name = ensure_candidate_portal_exists(doc)
    if not portal_name:
        frappe.throw("Could not create or find Candidate Portal for this Job Offer.")

    # Fetch Notification
    notification = frappe.get_doc("Notification", "LOI Letter Notification")

    subject = frappe.render_template(notification.subject, {"doc": doc})
    message = frappe.render_template(notification.message, {"doc": doc})

    # Add applicant email automatically to TO list
    if doc.applicant_email and doc.applicant_email not in to_users:
        to_users.append(doc.applicant_email)

    if not to_users:
        frappe.throw("No recipients found in TO users or applicant email.")

    # Prepare attachment
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

    # Send email
    frappe.sendmail(
        recipients=to_users,
        cc=cc_users,
        subject=subject,
        content=message,
        attachments=[attachment] if attachment else None
    )

    return "LOI Letter sent Successfully"


@frappe.whitelist()
def send_release_letter(name):
    doc = frappe.get_doc("Job Offer", name)
    
    # Ensure candidate portal exists before sending LOI
    portal_name = ensure_candidate_portal_exists(doc)
    if not portal_name:
        frappe.throw("Could not create or find Candidate Portal for this Job Offer.")
    
    notification = frappe.get_doc("Notification", "Release Offer Letter")
    subject = frappe.render_template(notification.subject, {"doc": doc})
    message = frappe.render_template(notification.message, {"doc": doc})
    # chang to cc users 
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
    return "Release Letter sent Successfully"


def set_salary_components_with_amount(doc):
    if not doc.custom_salary_structure:
        return

    # * Fetch Salary Structure
    doc._salary_structure_doc = frappe.get_doc("Salary Structure", doc.custom_salary_structure)

    # * Setup globals for formula evaluation
    doc.whitelisted_globals = {
        "int": int,
        "float": float,
        "long": int,
        "round": round,
        "rounded": rounded,
        "date": date,
        "getdate": getdate,
        "get_first_day": get_first_day,
        "get_last_day": get_last_day,
        "ceil": ceil,
        "floor": floor,
    }


    # Clear previous earnings/deductions
    doc.custom_earnings = []
    doc.custom_deductions = []
    total_gross_pay =0
    total_deductions = 0
    # * Prepare data for evaluation
    doc.data, doc.default_data = get_data_for_eval(doc, doc.custom_total_gross_pay)

    # * Add earnings
    for row in doc._salary_structure_doc.get("earnings", []):
        component = create_component_row(doc, row, "earnings")
        if component:
            doc.append("custom_earnings", component)
            doc.data.update({"gross_pay": total_gross_pay})
            if not component.get("do_not_include_in_total") and not component.get("statistical_component"):
                total_gross_pay += component.get("amount")

    doc.data.update({"gross_pay": total_gross_pay})
    # * Add deductions
    for row in doc._salary_structure_doc.get("deductions", []):
        component = create_component_row(doc,row, "deductions")
        if component:
            doc.append("custom_deductions", component)
            doc.data.update({"gross_pay": total_gross_pay})
            if not component.get("do_not_include_in_total") and not component.get("statistical_component"):
                total_deductions +=component.get("amount")

    doc.custom_total_gross_pay = total_gross_pay
    doc.custom_total_deductions = total_deductions


def create_component_row(doc, struct_row, component_type):
    """
    * Build a component row (earning or deduction) from Salary Structure row
    * Exclude formula, avoid statistical components, apply payment_days logic
    """

    # ? ONLY ADD ANNEXTURE TYPE EARNING AND DEDUCTIONS COMPONENT
    is_component_added= 1
    try:
        annexure_type = frappe.db.get_value("Salary Component", {"salary_component_abbr":struct_row.abbr}, "custom_annexure_type")
        if annexure_type in ["Earnings", "Deductions", "Employer Contributions"]:
            if component_type.lower() != annexure_type.lower():
                is_component_added = 0
        else:
            is_component_added = 0

    except:
        is_component_added = 1


    if not is_component_added:
        return

    amount = 0
    try:
        # Evaluate condition & formula
        condition = (struct_row.condition or "True").strip()
        formula = (struct_row.formula or "0").strip().replace("\r", "").replace("\n", "")
        if _safe_eval(condition, doc.whitelisted_globals, doc.data):
            amount = flt(
                _safe_eval(formula, doc.whitelisted_globals, doc.data),
                struct_row.precision("amount")
            )

    except Exception as e:
        frappe.throw(
            f"Error while evaluating the Salary Structure '{doc.custom_salary_structure}' at row {struct_row.idx}.\n"
            f"Component: {struct_row.salary_component}\n\n"
            f"Error: {e}\n\n"
            f"Hint: Check formula/condition syntax. Only valid Python expressions are allowed."
        )
    doc.default_data[struct_row.abbr] = flt(amount)
    doc.data[struct_row.abbr] = flt(amount)        
    # Skip statistical components
    if struct_row.statistical_component:
        if struct_row.depends_on_payment_days:
            payment_days_amount = (
                flt(amount) * flt(doc.data.get("payment_days", 30)) / cint(30)
            )
            doc.data[struct_row.abbr] = flt(payment_days_amount, struct_row.precision("amount"))
    # Skip zero-amount components (based on settings)
    remove_if_zero = frappe.get_cached_value(
        "Salary Component", struct_row.salary_component, "remove_if_zero_valued"
    )

    # ! IF CALCULATED AMOUNT IS ZERO AND NOT BASED ON FORMULA,
    # ! USE STATIC AMOUNT DEFINED IN THE SALARY COMPONENT
    if amount == 0 and not struct_row.amount_based_on_formula:
        amount = struct_row.amount
    
    if not (
        amount
        or (struct_row.amount_based_on_formula and amount is not None)
        or (not remove_if_zero and amount is not None)
    ):
        return None

    # Compute default_amount with default data
    try:
        default_amount = _safe_eval(
            (struct_row.formula or "0").strip(), doc.whitelisted_globals, doc.default_data
        )
    except Exception:
        default_amount = 0
    
    # Return final component row (formula is excluded)
    if not struct_row.statistical_component and not (remove_if_zero and not amount):
        return {
            "salary_component": struct_row.salary_component,
            "abbr": struct_row.abbr,
            "amount": flt(amount),
            "default_amount": flt(default_amount),
            "depends_on_payment_days": struct_row.depends_on_payment_days,
            "precision": struct_row.precision("amount"),
            "statistical_component": struct_row.statistical_component,
            "remove_if_zero_valued": remove_if_zero,
            "amount_based_on_formula": struct_row.amount_based_on_formula,
            "condition": struct_row.condition,
            "variable_based_on_taxable_salary": struct_row.variable_based_on_taxable_salary,
            "is_flexible_benefit": struct_row.is_flexible_benefit,
            "do_not_include_in_total": struct_row.do_not_include_in_total,
            "is_tax_applicable": struct_row.is_tax_applicable,
            "formula":formula
        }


def get_data_for_eval(doc, gross_pay=None):
    # * Create merged dict for salary component evaluation
    data = frappe._dict()
    if gross_pay:
        data.update({"gross_pay":gross_pay})

    # * Merge fields from current document
    data.update(doc.as_dict())
    data.update(SalarySlip.get_component_abbr_map(doc))

    if not data.get("base"):
        data["base"] = doc.custom_monthly_base_salary

    if doc.custom_variable:
        data["variable"] = doc.custom_variable

    if data.get("custom_meal_card_consesnt"):
        data["custom_meal_coupons"] = data.get("custom_meal_card_consesnt")

    # Prepare shallow copy for default data
    default_data = data.copy()
    # * Populate abbreviations
    for key in ("earnings", "deductions"):
        if doc.get(key):
            for d in doc.get(key):
                default_data[d.abbr] = d.default_amount or 0
                data[d.abbr] = d.amount or 0

    # * Set fallback defaults
    data.setdefault("total_working_days", 30)
    data.setdefault("leave_without_pay", 0)
    data.setdefault("custom_lop_days", 0)
    data.setdefault("custom_total_arrear_payable", 0)
    data.setdefault("absent_days", 0)
    data.setdefault("payment_days", 30)
    data.setdefault("custom_penalty_leave_days", 0)
    data.setdefault("custom_overtime", 0)
    return data, default_data

def did_change(doc, fields):
    if doc.is_new():
        return True

    old_doc = frappe.get_doc(doc.doctype, doc.name)
    for field in fields:
        if doc.get(field) != old_doc.get(field):
            print(doc.get(field), field)
            return True

    return False

def calculate_gross_pay_and_deductions(doc):
    total_gross_pay = 0
    total_deduction = 0

    if doc.get("custom_earnings"):
        for d in doc.get("custom_earnings"):
            if not d.do_not_include_in_total and not d.statistical_component:
                amount = flt(d.amount)   
                total_gross_pay += amount

    if doc.get("custom_deductions"):
        for d in doc.get("custom_deductions"):
            if not d.do_not_include_in_total and not d.statistical_component:
                amount = flt(d.amount)   
                total_deduction += amount

    doc.custom_total_gross_pay = total_gross_pay or 0
    doc.custom_total_deductions = total_deduction or 0

    doc.custom_net_pay = doc.custom_total_gross_pay - doc.custom_total_deductions


@frappe.whitelist()
def get_user_list(search=None):
    users = frappe.get_all(
        "User",
        filters={"enabled": 1},
        or_filters=[
            ["email", "like", f"%{search}%"],
            ["full_name", "like", f"%{search}%"]
        ],
        fields=["name as value", "full_name as description", "email"],
        limit_page_length=1000  # show up to 1000 users
    )

    # Format for MultiSelectList
    result = []
    for u in users:
        result.append({
            "value": u['value'],
            "description": u['description'] or u['value']
        })

    return result