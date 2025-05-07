import frappe
from prompt_hr.py.utils import validate_hash,send_notification_email
import json
from frappe import _


def get_context(context):
    # do your magic here
    pass


# ! prompt_hr.prompt_hr.web_form.candidate_portal.candidate_portal.validate_candidate_portal_hash
# ? FUNCTION TO VALIDATE CANDIDATE PORTAL HASH
@frappe.whitelist(allow_guest=True)
def validate_candidate_portal_hash(hash, doctype, child_doctype, filters, fields):
    # ? LOAD THE FIELDS IF THEY ARE IN JSON FORMAT
    fields = json.loads(fields) if isinstance(fields, str) else fields

    # ? VALIDATE THE HASH FOR A SPECIFIC DOCTYPE AND PRIMARY KEY
    if validate_hash(hash, doctype, filters):
        # ? GET FORM DATA BASED ON THE FILTERS AND FIELDS
        form_data = frappe.get_all(doctype, filters=filters, fields=fields)
        if not form_data:
            frappe.throw("Document not found")

        # ? GET THE CHILD DATA BASED ON THE FORM DATA
        child_table_data = frappe.db.get_all(
            child_doctype, filters={"parent": form_data[0].get("name")}, fields=["*"]
        )

        # ? COMBINE THE FORM AND CHILD DATA IN A SINGLE DICT
        data = {"form_data": form_data, "child_table_data": child_table_data}
        # ? RETURN THE COMBINED DATA
        return data
    else:
        frappe.throw("Invalid hash")


def update_job_offer(
    job_offer,
    expected_date_of_joining,
    offer_acceptance,
    condition_for_offer_acceptance,
):

    frappe.db.set_value(
        "Job Offer",
        job_offer,
        "custom_candidate_date_of_joining",
        expected_date_of_joining,
    )
    frappe.db.set_value(
        "Job Offer", job_offer, "custom_candidate_offer_acceptance", offer_acceptance
    )
    frappe.db.set_value(
        "Job Offer",
        job_offer,
        "custom_candidate_condition_for_offer_acceptance",
        condition_for_offer_acceptance,
    )


# ! prompt_hr.py.candidate_portal.update_candidate_portal
# ? FUNCTION TO UPDATE ONLY 'documents' CHILD TABLE IN CANDIDATE PORTAL
@frappe.whitelist()
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

        update_job_offer(
            doc.job_offer,
            doc.expected_date_of_joining,
            doc.offer_acceptance,
            doc.condition_for_offer_acceptance,
        )

        # ? VALIDATE 'documents' CHILD TABLE DATA
        documents = doc.get("documents")
        if not isinstance(documents, list):
            return {"success": False, "message": "'documents' must be a list"}

        # ? RESET EXISTING CHILD TABLE
        portal_doc.set("documents", [])

        # ? APPEND EACH DOCUMENT ENTRY
        for row in documents:
            row["upload_date"] = frappe.utils.now()
            row["upload_time"] = frappe.utils.now()
            row["ip_address_on_document_upload"] = frappe.local.request_ip
            portal_doc.append("documents", row)

        # ? SEND MAIL TO HR
        send_notification_email(
            notification_name="HR Candidate Web Form Revert Mail",
            recipients=[portal_doc.applicant_email],
            button_label="View Details",
            doctype="Candidate Portal",
            docname=portal_doc.name,
        )
        # ? SAVE DOCUMENT WITH IGNORED PERMISSIONS
        portal_doc.save(ignore_permissions=True)

        return {"success": True, "message": "Documents updated successfully"}

    except Exception as e:
        # ? LOG ERROR IF SOMETHING FAILS
        frappe.log_error(frappe.get_traceback(), "Candidate Portal Update Error")
        return {"success": False, "message": f"Error updating documents: {str(e)}"}
