import frappe
from prompt_hr.py.utils import validate_hash, send_notification_email, get_hr_managers_by_company
import json
from frappe import _
from datetime import datetime


def get_context(context):
    # do your magic here
    pass


# ! prompt_hr.prompt_hr.web_form.candidate_portal.candidate_portal.validate_candidate_portal_hash
# ? FUNCTION TO VALIDATE CANDIDATE PORTAL HASH
@frappe.whitelist(allow_guest=True)
def validate_candidate_portal_hash(
    hash, doctype, child_doctypes_config, filters, fields
):
    # ? LOAD THE FIELDS IF THEY ARE IN JSON FORMAT
    fields = json.loads(fields) if isinstance(fields, str) else fields
    child_doctypes_config = json.loads(child_doctypes_config) if isinstance(child_doctypes_config, str) else child_doctypes_config

    # ? VALIDATE THE HASH FOR A SPECIFIC DOCTYPE AND PRIMARY KEY
    if validate_hash(hash, doctype, filters):
        # ? GET FORM DATA BASED ON THE FILTERS AND FIELDS
        form_data = frappe.get_all(doctype, filters=filters, fields=fields)
        if not form_data:
            frappe.throw("Document not found")

        child_tables_data = []

        for child_doctype_config in child_doctypes_config:
            # ? GET THE CHILD DATA BASED ON THE FORM DATA
            child_table_data = frappe.db.get_all(
                child_doctype_config["child_doctype"],
                filters={
                    "parent": form_data[0].get("name"),
                    "parentfield": child_doctype_config["child_table_fieldname"],
                },
                fields=["*"],
            )
            child_tables_data.append(
                {
                    "child_doctype": child_doctype_config["child_doctype"],
                    "child_table_data": child_table_data,
                    "child_table_fieldname": child_doctype_config["child_table_fieldname"],
                }
            )

        # ? COMBINE THE FORM AND CHILD DATA IN A SINGLE DICT
        data = {"form_data": form_data, "child_tables_data": child_tables_data}
        # ? RETURN THE COMBINED DATA
        return data
    else:
        frappe.throw("Invalid hash")

# ? FUNCTION TO UPDATE JOB OFFER FIELDS
@frappe.whitelist()
def update_job_offer(
    job_offer,
    expected_date_of_joining,
    offer_acceptance,
    condition_for_offer_acceptance,
):
    try:
        if not job_offer:
            frappe.throw(_("Job Offer ID is required"))

        if not frappe.db.exists("Job Offer", job_offer):
            frappe.throw(_("Job Offer {0} does not exist").format(job_offer))

       

        # ? UPDATE FIELDS
        frappe.db.set_value(
            "Job Offer",
            job_offer,
            "custom_candidate_date_of_joining",
            expected_date_of_joining,
        )
        frappe.db.set_value(
            "Job Offer",
            job_offer,
            "custom_candidate_offer_acceptance",
            offer_acceptance,
        )
        frappe.db.set_value(
            "Job Offer",
            job_offer,
            "custom_candidate_condition_for_offer_acceptance",
            condition_for_offer_acceptance,
        )

        return {
            "status": "success",
            "message": _("Job Offer updated successfully")
        }

    except Exception:
        frappe.log_error(frappe.get_traceback(), "Error Updating Job Offer")
        return {
            "status": "error",
            "message": _("Something went wrong while updating the Job Offer.")
        }



# ! prompt_hr.py.candidate_portal.update_candidate_portal
# ? FUNCTION TO UPDATE CHILD TABLES IN CANDIDATE PORTAL
@frappe.whitelist(allow_guest=True)
def update_candidate_portal(doc):
    try:
        # ? PARSE JSON IF COMING AS STRING
        if isinstance(doc, str):
            doc = frappe.parse_json(doc)

        # ? GET DOCUMENT NAME
        doc_name = doc.get("name")
        if not doc_name:
            return {"success": False, "message": "Document name is required"}

        # ? FETCH DOCUMENT OR THROW IF NOT FOUND
        portal_doc = frappe.get_doc("Candidate Portal", doc_name)

        # ? UPDATE JOB OFFER IF EXISTS
        job_offer = frappe.db.get_value("Candidate Portal", doc_name, "job_offer")
        if job_offer:
            update_job_offer(
                job_offer,
                doc.get("expected_date_of_joining"),
                doc.get("offer_acceptance"),
                doc.get("condition_for_offer_acceptance"),
            )

        # ? UPDATE documents CHILD TABLE
        documents = doc.get("documents")
        if documents is not None:
            if not isinstance(documents, list):
                return {"success": False, "message": "'documents' must be a list"}
            
            # ? RESET EXISTING documents CHILD TABLE
            portal_doc.set("documents", [])
            
            # ? APPEND EACH DOCUMENT ENTRY
            for row in documents:
                if isinstance(row, dict):
                    row["upload_date"] = frappe.utils.now()
                    row["upload_time"] = frappe.utils.now()
                    row["ip_address_on_document_upload"] = frappe.local.request_ip
                    portal_doc.append("documents", row)

        # ? UPDATE new_joinee_documents CHILD TABLE
        new_joinee_documents = doc.get("new_joinee_documents")
        if new_joinee_documents is not None:
            if not isinstance(new_joinee_documents, list):
                return {"success": False, "message": "'new_joinee_documents' must be a list"}
            
            # ? RESET EXISTING new_joinee_documents CHILD TABLE
            portal_doc.set("new_joinee_documents", [])
            
            # ? APPEND EACH NEW JOINEE DOCUMENT ENTRY
            for row in new_joinee_documents:
                if isinstance(row, dict):
                    row["upload_date"] = frappe.utils.now()
                    row["upload_time"] = frappe.utils.now()
                    row["ip_address_on_document_upload"] = frappe.local.request_ip
                    portal_doc.append("new_joinee_documents", row)

        # ? UPDATE OTHER FORM FIELDS
        updatable_fields = [
            "offer_acceptance",
            "expected_date_of_joining", 
            "condition_for_offer_acceptance"
        ]
        
        for field in updatable_fields:
            if field in doc:
                setattr(portal_doc, field, doc.get(field))

        # ? SAVE DOCUMENT WITH IGNORED PERMISSIONS
        portal_doc.save(ignore_permissions=True)

        # ? SEND MAIL TO HR
        try:
            send_notification_email(
                notification_name="HR Candidate Web Form Revert Mail",
                recipients=get_hr_managers_by_company(portal_doc.company),
                button_label="View Details",
                doctype="Candidate Portal",
                docname=portal_doc.name,
            )
        except Exception as email_error:
            # ? LOG EMAIL ERROR BUT DON'T FAIL THE ENTIRE UPDATE
            frappe.log_error(f"Failed to send notification email: {str(email_error)}", "Email Notification Error")

        return {"success": True, "message": "Information updated successfully"}

    except Exception as e:
        # ? LOG ERROR IF SOMETHING FAILS
        frappe.log_error(frappe.get_traceback(), "Candidate Portal Update Error")
        return {"success": False, "message": f"Error updating information: {str(e)}"}