import frappe
import hmac
import hashlib
import json
import traceback


# ? FUNCTION TO GENERATE HMAC HASH FROM INPUT USING SITE SECRET
def create_hash(input_text: str) -> str:
    hash_secret = frappe.local.conf.get("hash_secret_key")
    if not hash_secret:
        frappe.throw("Hash secret not found in site_config.json")

    # ? CREATE FULL HASH, THEN TRIM TO 12 CHARACTERS
    full_hash = hmac.new(
        key=hash_secret.encode('utf-8'),
        msg=input_text.strip().encode('utf-8'),
        digestmod=hashlib.sha256
    ).hexdigest()

    return full_hash[:12]


# ? FUNCTION TO VERIFY IF PROVIDED INPUT MATCHES THE EXPECTED HASH
def verify_hash(input_text: str, hash_to_check: str) -> bool:
    generated_hash = create_hash(input_text)
    return hmac.compare_digest(generated_hash, hash_to_check)


# ! prompt_hr.py.utils.validate_hash
# ? FUNCTION TO VALIDATE THE HASH FOR A SPECIFIC DOCTYPE AND PRIMARY KEY
@frappe.whitelist(allow_guest=True)
def validate_hash(hash, doctype, filters):
    try:
        # ? DESERIALIZE JSON STRING TO DICT
        filters_dict = json.loads(filters)

        # ? GET DOCUMENT NAME USING DOCTYPE AND FILTERS
        docname = frappe.db.get_value(doctype, filters_dict, "name")

        if not docname:
            frappe.throw("Document not found")

        # ? GENERATE THE HASH FOR THE DOCUMENT NAME
        generated_hash = create_hash(docname)

        # ? COMPARE THE GENERATED HASH WITH THE PROVIDED HASH
        if not hmac.compare_digest(generated_hash, hash):
            frappe.throw("Invalid hash")

        return True

    except Exception:
        frappe.log_error(frappe.get_traceback(), "Hash Validation Error")
        frappe.throw("Something went wrong during hash validation")


# ? FUNCTION TO SEND FULLY DYNAMIC NOTIFICATION EMAIL
def send_notification_email(
    recipients,
    notification_name=None,
    doctype=None,
    docname=None,
    button_label="View Details",
    button_link = "None",
    fallback_subject="Notification",
    fallback_message="You have a new update. Please check your portal.",
    extra_context=None,
    hash_input_text=None,
):

    try:
        hash = None
        base_url = frappe.utils.get_url()

        # ? LOAD DOCUMENT IF PROVIDED
        doc = frappe.get_doc(doctype, docname) if doctype and docname else frappe._dict({})

        if button_link == "None":
            # ? AUTO-BUILD LINK TO THE DOCUMENT
            button_link = f"{base_url}/app/{doctype.lower().replace(' ', '-')}/{docname}" if doctype and docname else None

        # ? BASE CONTEXT
        context = {
            "doc": doc,
            "doctype": doctype,
            "docname": docname,
            "button_label": button_label,
            "button_link": button_link,
            "base_url": base_url,
        }

        # ? ADD HASH TO CONTEXT IF PROVIDED
        if hash_input_text:
            hash = create_hash(hash_input_text)

        # ? MERGE ANY ADDITIONAL CONTEXT
        if extra_context:
            context.update(extra_context)

        # ? LOAD NOTIFICATION DOC IF AVAILABLE
        notification_doc = None
        if notification_name:
            result = frappe.get_all("Notification", filters={"name": notification_name}, limit=1)
            if result:
                notification_doc = frappe.get_doc("Notification", result[0].name)

        # ? SEND EMAILS
        for email in recipients:
            context["user"] = email
            hash_message = None

            if notification_doc:
                subject = frappe.render_template(notification_doc.subject or fallback_subject, context)
                message = frappe.render_template(notification_doc.message or fallback_message, context)
            else:
                subject = fallback_subject
                message = fallback_message

            if hash:
              hash_message = f"<p>Password: <b>{hash}</b></p>"
            # ? APPEND ACTION BUTTON IF WE HAVE A LINK
            if button_link:
                message += f"""
                    <hr>
                    {hash_message or ""}
                    <p><b>{button_label}</b></p>
                    <p><a href="{button_link}" target="_blank">{button_label}</a></p>
                """

            frappe.sendmail(
                recipients=[email],
                subject=subject,
                message=message
            )

        # ? LOG SUCCESS
        frappe.log_error(
            title="Notification Sent",
            message=f"Sent dynamic notification to {len(recipients)} recipient(s)."
        )

    except Exception as e:
        frappe.log_error(
            title="Notification Email Error",
            message=f"Failed sending notification: {str(e)}\n{traceback.format_exc()}"
        )

import frappe
from frappe import _

@frappe.whitelist()
def get_checklist_documents(checklist):
    """Fetch documents from a Joining Document Checklist with proper permission handling"""
    try:
        
        documents = frappe.db.get_all("Joining Document",
            filters={"parent": checklist},
            fields=["required_document", "document_collection_stage"],
        )
        if not documents:
            return {"error": 1, "message": _("No documents found for the provided checklist.")}
        return {"documents": documents}
    except Exception as e:
        frappe.log_error(f"Error fetching checklist documents: {str(e)}")
        return {"error": str(e)}

# ? FUNCTION TO INVITE CANDIDATE FOR DOCUMENT COLLECTION
@frappe.whitelist()
def invite_for_document_collection(args, joining_document_checklist, document_collection_stage=None, documents=None):
    try:
        # ? CONVERT ARGS TO DICT IF IT'S A STRING
        if isinstance(args, str):
            args = frappe.parse_json(args)

        # ? CONVERT DOCUMENTS TO LIST IF IT'S A STRING
        if isinstance(documents, str):
            documents = frappe.parse_json(documents)

        # ? FETCH FIELDS FROM JOB APPLICANT
        job_applicant = frappe.db.get_value(
            "Job Applicant",
            args.get("name"),
            ["email_id", "phone_number", "applicant_name", "designation"],
            as_dict=True
        )

        if not job_applicant:
            return "Job Applicant not found."

        # ? CHECK IF ALREADY INVITED
        existing = frappe.db.exists("Candidate Portal", {
            "applicant_email": job_applicant.email_id,
        })

        if existing:
            # ? UPDATE EXISTING RECORD
            invitation = frappe.get_doc("Candidate Portal", existing)

            invitation.phone_number = job_applicant.phone_number
            invitation.applicant_name = job_applicant.applicant_name
            invitation.applied_for_designation = job_applicant.designation
            invitation.joining_document_checklist = joining_document_checklist
            invitation.document_collection_stage = document_collection_stage

            # ? FETCH EXISTING REQUIRED DOCUMENTS
            existing_required_docs = {d.required_document for d in invitation.documents}

            # ? APPEND ONLY NEW DOCUMENTS
            if documents:
                new_docs_seen = set()
                for doc in documents:
                    req_doc = doc.get("required_document")
                    if req_doc and req_doc not in existing_required_docs and req_doc not in new_docs_seen:
                        invitation.append("documents", {
                            "required_document": req_doc,
                            "document_collection_stage": doc.get("document_collection_stage")
                        })
                        new_docs_seen.add(req_doc)

            invitation.save(ignore_permissions=True)
            frappe.db.commit()
            return "Invitation updated successfully."

        else:
            # ? CREATE NEW INVITATION
            invitation = frappe.new_doc("Candidate Portal")
            invitation.applicant_email = job_applicant.email_id
            invitation.phone_number = job_applicant.phone_number
            invitation.applicant_name = job_applicant.applicant_name
            invitation.applied_for_designation = job_applicant.designation
            invitation.joining_document_checklist = joining_document_checklist
            invitation.document_collection_stage = document_collection_stage

            # ? ADD UNIQUE DOCUMENTS
            if documents:
                seen_docs = set()
                for doc in documents:
                    req_doc = doc.get("required_document")
                    if req_doc and req_doc not in seen_docs:
                        invitation.append("documents", {
                            "required_document": req_doc,
                            "document_collection_stage": doc.get("document_collection_stage")
                        })
                        seen_docs.add(req_doc)
            

            invitation.insert(ignore_permissions=True)
            frappe.db.commit()
            return "Invitation sent successfully."

    except Exception as e:
        frappe.log_error(f"Error inviting for document collection: {str(e)}")
        return "An error occurred while inviting for document collection."
